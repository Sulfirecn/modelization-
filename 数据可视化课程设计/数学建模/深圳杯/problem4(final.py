import numpy as np
import pandas as pd
import pymc as pm

import matplotlib.pyplot as plt
import warnings
import re
import os


warnings.filterwarnings("ignore")

# 假设有降噪前和降噪后的数据文件
NOISY_DATA_PATH = "附件1：不同人数的STR图谱数据.xlsx"  # 替换为实际路径
DENOISED_DATA_PATH = "附件4：去噪后的STR图谱数据.xlsx"  # 替换为实际路径


class BayesianSTRDenoiser:
    def __init__(self, noisy_data_path, denoised_data_path):
        """
        初始化降噪器
        """
        # 先初始化阈值属性
        self.thresholds = {
            'B': 50,  # 蓝色通道阈值 (RFU)
            'G': 40,  # 绿色通道阈值
            'Y': 60,  # 黄色通道阈值
            'R': 70,  # 红色通道阈值
            'global_min': 30  # 全局最小阈值
        }

        # 然后加载数据
        self.noisy_data = self._load_data(noisy_data_path)
        self.denoised_data = self._load_data(denoised_data_path) if denoised_data_path else pd.DataFrame()
        self.prior_knowledge = {}
        self.trace = None
        self.model = None
        self.model_trained = False
        self.stutter_stats = None

        print(f"噪声数据行数: {len(self.noisy_data)}")
        print(f"降噪数据行数: {len(self.denoised_data)}")
        if not self.denoised_data.empty:
            print("降噪数据显示:")
            print(self.denoised_data.head())

    def get_height_stats(self):
        """获取高度统计信息，帮助设置合理阈值"""
        if self.noisy_data.empty:
            print("警告: 噪声数据为空")
            return None

        try:
            if 'Height' in self.noisy_data.columns:
                return self.noisy_data['Height'].describe()
            else:
                print("警告: 数据中无Height列")
                return None
        except AttributeError as e:
            print(f"获取高度统计失败: {e}")
            return None

    def _load_data(self, file_path):
        """
        加载STR数据 - 专门处理包含'allele x','size x','height x'格式的宽表
        """
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return pd.DataFrame()

        # 读取Excel文件
        try:
            df = pd.read_excel(file_path)
            print(f"成功读取文件: {file_path}，形状: {df.shape}")
        except Exception as e:
            print(f"读取文件失败: {e}")
            return pd.DataFrame()

        # 检查基础列是否存在
        required_base_cols = ['Sample File', 'Marker', 'Dye']
        for col in required_base_cols:
            if col not in df.columns:
                print(f"缺少必需列: {col}, 尝试在列名中搜索匹配项...")

                # 尝试寻找可能的匹配列
                possible_cols = {
                    'Sample File': ['Sample File', '样本文件', 'sample_file', 'SampleFile'],
                    'Marker': ['Marker', '位点', '基因座', 'marker'],
                    'Dye': ['Dye', '染料', 'Color', '染料通道']
                }

                found = False
                for possible in possible_cols[col]:
                    if possible in df.columns:
                        df = df.rename(columns={possible: col})
                        print(f"重命名列: '{possible}' -> '{col}'")
                        found = True
                        break
                if not found:
                    print(f"警告: 找不到必需的列: {col}。实际列名: {df.columns.tolist()}")
                    print("尝试使用前3列作为基础列...")
                    # 尝试使用前3列作为基础列
                    if len(df.columns) >= 3:
                        df.columns = ['Sample', 'Marker', 'Dye'] + list(df.columns[3:])
                        print("使用前3列作为基础列")
                    else:
                        print("错误: 数据列不足")
                        return pd.DataFrame()

        # 确保基础列名正确
        if 'Sample File' in df.columns:
            df.rename(columns={'Sample File': 'Sample'}, inplace=True)
        if 'SampleFile' in df.columns:
            df.rename(columns={'SampleFile': 'Sample'}, inplace=True)
        if 'Marker' not in df.columns:
            if '基因座' in df.columns:
                df.rename(columns={'基因座': 'Marker'}, inplace=True)
            elif '位点' in df.columns:
                df.rename(columns={'位点': 'Marker'}, inplace=True)
        if 'Dye' not in df.columns:
            if '染料' in df.columns:
                df.rename(columns={'染料': 'Dye'}, inplace=True)
            elif '染料通道' in df.columns:
                df.rename(columns={'染料通道': 'Dye'}, inplace=True)

        # 识别等位基因相关列（Allele X, Size X, Height X）
        allele_cols = [col for col in df.columns if re.match(r'^Allele\s*\d+$', col, re.IGNORECASE)]
        size_cols = [col for col in df.columns if re.match(r'^Size\s*\d+$', col, re.IGNORECASE)]
        height_cols = [col for col in df.columns if re.match(r'^Height\s*\d+$', col, re.IGNORECASE)]

        # 如果没有匹配到列名，尝试使用固定列数
        if not allele_cols or not size_cols or not height_cols:
            print("警告: 无法识别Allele/Size/Height列，使用固定列数模式")
            # 假设前30组数据（每组3列）
            all_cols = df.columns.tolist()
            num_groups = min(30, (len(all_cols) - 3) // 3)  # 最多30组

            allele_cols = [all_cols[3 + i * 3] for i in range(num_groups)]
            size_cols = [all_cols[3 + i * 3 + 1] for i in range(num_groups)]
            height_cols = [all_cols[3 + i * 3 + 2] for i in range(num_groups)]
            print(f"固定模式使用 {len(allele_cols)} 组列")

        # 按数字后缀排序
        def extract_number(col_name):
            match = re.search(r'\d+$', col_name)
            return int(match.group()) if match else 0

        allele_cols = sorted(allele_cols, key=extract_number)
        size_cols = sorted(size_cols, key=extract_number)
        height_cols = sorted(height_cols, key=extract_number)

        # 只取前30个等位基因
        num_alleles = min(30, len(allele_cols))
        allele_cols = allele_cols[:num_alleles]
        size_cols = size_cols[:num_alleles]
        height_cols = height_cols[:num_alleles]

        print(f"使用 {num_alleles} 个等位基因点")

        # 转换宽表为长表 - 每种染料一行表示一个等位基因
        long_data = []
        for i in range(num_alleles):
            # 提取当前等位基因的三列数据
            temp_df = df[['Sample', 'Marker', 'Dye',
                          allele_cols[i], size_cols[i], height_cols[i]]].copy()

            # 重命名列
            temp_df.columns = ['Sample', 'Marker', 'Dye', 'Allele', 'Size', 'Height']

            # 移除完全为空的行
            temp_df = temp_df.dropna(subset=['Allele', 'Size', 'Height'], how='all')
            long_data.append(temp_df)

        # 合并所有数据
        if long_data:
            final_df = pd.concat(long_data, ignore_index=True)
        else:
            print("警告: 没有有效数据行")
            return pd.DataFrame()

        # 处理特殊值
        final_df['Allele'] = final_df['Allele'].replace(['OL', 'Off Ladder'], np.nan)
        try:
            final_df['Allele'] = pd.to_numeric(final_df['Allele'], errors='coerce')
        except:
            print("等位基因转换数值失败，使用原始值")

        # 转换数值类型
        final_df['Size'] = pd.to_numeric(final_df['Size'], errors='coerce')
        final_df['Height'] = pd.to_numeric(final_df['Height'], errors='coerce')

        # 处理缺失值
        final_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        final_df.dropna(subset=['Size', 'Height'], how='all', inplace=True)

        # 添加高度统计
        if not final_df.empty and 'Height' in final_df.columns:
            height_stats = final_df['Height'].describe()
            print(
                f"高度统计: 最小值={height_stats['min']:.2f}, 均值={height_stats['mean']:.2f}, 最大值={height_stats['max']:.2f}")

            # 自适应调整阈值
            self.thresholds['global_min'] = max(30, height_stats['mean'] * 0.1)
            print(f"自适应设置全局最小阈值为: {self.thresholds['global_min']:.2f}")

        print(f"处理后数据形状: {final_df.shape}")
        return final_df

    def extract_prior_knowledge(self):
        """
        从降噪后数据中提取先验知识，重点提取脱扣峰统计
        """
        if self.denoised_data.empty:
            print("警告: 降噪数据为空，使用默认先验知识")
            return self._get_default_prior_knowledge()

        print("从降噪数据中提取脱扣峰统计...")

        df = self.denoised_data.copy()

        # 确保有足够数据提取脱扣峰
        if df.empty:
            print("警告: 降噪数据为空，无法提取脱扣峰统计")
            return self._get_default_stutter_stats()

        # 提取脱扣峰统计
        stutter_stats = self._extract_stutter_stats(df)
        self.stutter_stats = stutter_stats
        print(f"提取到 {len(stutter_stats)} 个脱扣峰统计数据")

        # 保存先验知识
        self.prior_knowledge = {
            'stutter_stats': stutter_stats
        }

        print("先验知识提取完成")
        return self.prior_knowledge

    def _extract_stutter_stats(self, df):
        """
        从数据中提取脱扣峰统计数据
        """
        stutter_data = []

        # 确保有必要的列
        required_cols = ['Sample', 'Marker', 'Dye', 'Allele', 'Height']
        if not all(col in df.columns for col in required_cols):
            print("警告: 缺少提取脱扣峰所需的列")
            return self._get_default_stutter_stats()

        # 处理每个样本-标记组合
        for (sample, marker), group in df.groupby(['Sample', 'Marker']):
            # 确保有至少两个峰来分析脱扣峰
            if len(group) < 2:
                continue

            # 按等位基因排序
            group = group.sort_values('Allele')
            group = group.reset_index(drop=True)

            # 获取主峰位置（高度最大的峰）
            main_peak_idx = group['Height'].idxmax()
            main_allele = group.loc[main_peak_idx, 'Allele']
            main_height = group.loc[main_peak_idx, 'Height']

            # 查找可能的脱扣峰（在相同位置但更小的峰）
            for i in range(len(group)):
                if i == main_peak_idx:
                    continue  # 跳过主峰

                current_allele = group.loc[i, 'Allele']
                current_height = group.loc[i, 'Height']
                dye = group.loc[i, 'Dye']

                # 计算与主峰的距离
                allele_diff = abs(current_allele - main_allele)

                # 只考虑在距离内且高度小于主峰的峰
                if 0.5 <= allele_diff <= 5.0 and current_height < main_height:
                    stutter_ratio = current_height / main_height

                    # 确保比率合理
                    if 0.001 < stutter_ratio < 1.0:
                        stutter_data.append({
                            'Marker': marker,
                            'Dye': dye,
                            'AlleleDiff': allele_diff,
                            'StutterRatio': stutter_ratio
                        })

        # 如果没有找到脱扣峰，使用默认值
        if not stutter_data:
            print("警告: 未提取到脱扣峰数据，使用默认值")
            return self._get_default_stutter_stats()

        # 转换为DataFrame
        stutter_df = pd.DataFrame(stutter_data)

        # 计算每个Marker-Dye组合的平均脱扣比率
        stats = []
        markers = stutter_df['Marker'].unique()
        dyes = stutter_df['Dye'].unique()

        for marker in markers:
            for dye in dyes:
                marker_dye_data = stutter_df[(stutter_df['Marker'] == marker) & (stutter_df['Dye'] == dye)]
                if not marker_dye_data.empty:
                    mean_ratio = marker_dye_data['StutterRatio'].mean()
                    std_ratio = marker_dye_data['StutterRatio'].std()

                    # 处理标准差为NaN的情况
                    if np.isnan(std_ratio):
                        std_ratio = max(0.05, mean_ratio * 0.3)

                    stats.append({
                        'Marker': marker,
                        'Dye': dye,
                        'MeanRatio': mean_ratio,
                        'StdRatio': std_ratio
                    })

        # 确保有统计数据
        if not stats:
            return self._get_default_stutter_stats()

        return pd.DataFrame(stats)

    def _get_default_prior_knowledge(self):
        """获取默认先验知识"""
        print("使用默认先验知识")
        return {'stutter_stats': self._get_default_stutter_stats()}

    def _get_default_stutter_stats(self):
        """获取默认脱扣峰统计"""
        print("使用默认脱扣峰统计")
        markers = ['D8S1179', 'D21S11', 'D7S820', 'CSF1PO', 'D3S1358',
                   'TH01', 'D13S317', 'D16S539', 'D2S1338', 'D19S433',
                   'vWA', 'TPOX', 'D18S51', 'AMEL', 'D5S818', 'FGA']
        return pd.DataFrame({
            'Marker': markers,
            'Dye': ['B'] * len(markers),
            'MeanRatio': [0.15] * len(markers),
            'StdRatio': [0.05] * len(markers)
        })

    def preprocess_noisy_data(self, df):
        """
        预处理噪声数据，添加特征用于脱扣峰检测
        """
        if df.empty:
            print("警告: 输入数据为空")
            return df

        print(f"预处理噪声数据，原始形状: {df.shape}")

        processed_df = df.copy()

        # 1. 根据染料通道设置初始阈值
        if 'Dye' in processed_df.columns and 'Height' in processed_df.columns:
            def apply_threshold(row):
                dye = row['Dye']
                min_threshold = self.thresholds.get(dye, self.thresholds['global_min'])
                return row['Height'] >= min_threshold

            processed_df['IsSignal'] = processed_df.apply(apply_threshold, axis=1)
            signal_count = processed_df['IsSignal'].sum()
            print(f"信号点数量: {signal_count}/{len(processed_df)}")

            # 如果信号点太少，调整阈值
            if signal_count < len(processed_df) * 0.1:  # 少于10%的点被检测为信号
                print(f"信号点太少 ({signal_count})，降低全局阈值")
                self.thresholds['global_min'] = max(20, self.thresholds['global_min'] * 0.8)
                processed_df['IsSignal'] = processed_df.apply(
                    lambda row: row['Height'] >= self.thresholds['global_min'], axis=1)
                print(f"新阈值: {self.thresholds['global_min']}, 新信号点: {processed_df['IsSignal'].sum()}")
        else:
            print("警告: 缺少染料或高度列，跳过信号检测")
            processed_df['IsSignal'] = False

        # 2. 峰间距分析
        processed_df['SizeDiff'] = 0.0
        processed_df['HeightRatio'] = 0.0
        processed_df['IsStutter'] = False

        if 'Size' in processed_df.columns and 'Height' in processed_df.columns:
            # 先排序
            processed_df.sort_values(['Sample', 'Marker', 'Size'], inplace=True)

            # 计算尺寸差
            processed_df['SizeDiff'] = processed_df.groupby(['Sample', 'Marker'])['Size'].diff().abs()

            # 计算高度比率
            for idx, group in processed_df.groupby(['Sample', 'Marker']):
                if len(group) > 1:
                    # 获取该组最大高度
                    max_height = group['Height'].max()
                    # 计算每个峰与最大峰的高度比
                    processed_df.loc[group.index, 'HeightRatio'] = group['Height'] / max_height
        else:
            print("警告: 缺少尺寸或高度列，跳过尺寸差异和高度比计算")

        # 3. 标记可能的脱扣峰
        processed_df = self._premark_stutter(processed_df)

        print(f"预处理完成，形状: {processed_df.shape}")
        return processed_df

    def _premark_stutter(self, df):
        """
        预标记可能的脱扣峰
        """
        if df.empty or 'HeightRatio' not in df.columns or 'SizeDiff' not in df.columns:
            return df

        # 使用提取的脱扣峰统计数据
        if self.stutter_stats is None:
            print("警告: 无脱扣峰统计数据，使用默认值预标记")
            stutter_stats = self._get_default_stutter_stats()
        else:
            stutter_stats = self.stutter_stats

        # 创建脱扣统计字典
        stutter_dict = {}
        if not stutter_stats.empty:
            for _, row in stutter_stats.iterrows():
                key = (row['Marker'], row['Dye'])
                stutter_dict[key] = (row['MeanRatio'], row['StdRatio'])

        # 标记可能的脱扣峰
        df['IsStutter'] = False

        # 对每个样本和标记进行处理
        for (sample, marker), group in df.groupby(['Sample', 'Marker']):
            if len(group) < 2:
                continue

            # 获取染料
            dye = group['Dye'].iloc[0] if 'Dye' in group.columns else 'B'

            # 获取脱扣参数
            stutter_key = (marker, dye)
            if stutter_key in stutter_dict:
                stutter_mean, stutter_std = stutter_dict[stutter_key]
                stutter_threshold = stutter_mean + 1.5 * stutter_std

                # 按尺寸排序
                sorted_group = group.sort_values('Size')

                # 找出主峰（高度最大）
                main_peak_idx = sorted_group['Height'].idxmax()
                main_allele = sorted_group.loc[main_peak_idx, 'Allele']
                main_height = sorted_group.loc[main_peak_idx, 'Height']

                for i, row in sorted_group.iterrows():
                    if i == main_peak_idx:
                        continue  # 跳过主峰

                    allele_diff = abs(row['Allele'] - main_allele)
                    height_ratio = row['Height'] / main_height

                    # 检查是否符合脱扣峰特征
                    if (0.5 < allele_diff < 5.0 and
                            height_ratio < stutter_threshold):
                        df.loc[i, 'IsStutter'] = True

        return df

    def train_model(self, samples=1000, tune=500):
        """
        训练贝叶斯模型，重点关注脱扣峰检测
        """
        if self.noisy_data.empty:
            print("警告: 噪声数据为空，无法训练模型")
            return None

        # 预处理噪声数据
        noisy_df = self.preprocess_noisy_data(self.noisy_data.copy())

        if noisy_df.empty:
            print("警告: 预处理后噪声数据为空")
            return None

        # 确保有足够的标记点用于训练
        if 'IsStutter' not in noisy_df.columns:
            print("警告: 无脱扣峰标记，无法训练模型")
            return None

        # 获取脱扣峰索引
        stutter_idx = noisy_df.index[noisy_df['IsStutter']].tolist()
        non_stutter_idx = noisy_df.index[~noisy_df['IsStutter']].tolist()

        print(f"开始训练模型... 数据点: {len(noisy_df)}, 脱扣峰: {len(stutter_idx)}, 非脱扣峰: {len(non_stutter_idx)}")

        try:
            with pm.Model() as stutter_model:
                # 使用HeightRatio特征来区分脱扣峰
                height_ratios = noisy_df['HeightRatio'].values

                # 脱扣峰分布
                stutter_mean = pm.Normal('stutter_mean', mu=0.15, sigma=0.1)
                stutter_sigma = pm.HalfNormal('stutter_sigma', sigma=0.1)

                # 非脱扣峰分布
                non_stutter_mean = pm.Normal('non_stutter_mean', mu=0.7, sigma=0.3)
                non_stutter_sigma = pm.HalfNormal('non_stutter_sigma', sigma=0.2)

                # 混合权重
                p_stutter = pm.Beta('p_stutter', alpha=1, beta=5)  # 假设脱扣峰较少

                # 每个点的类别变量
                category = pm.Bernoulli('category', p=p_stutter, shape=len(noisy_df))

                # 似然函数
                stutter_dist = pm.Normal.dist(mu=stutter_mean, sigma=stutter_sigma)
                non_stutter_dist = pm.Normal.dist(mu=non_stutter_mean, sigma=non_stutter_sigma)

                y = pm.Mixture('y', w=[category, 1 - category],
                               comp_dists=[stutter_dist, non_stutter_dist],
                               observed=height_ratios)

                self.model = stutter_model
                print("贝叶斯脱扣峰模型构建完成")

                # 训练模型
                self.trace = pm.sample(
                    samples,
                    tune=tune,
                    target_accept=0.9,
                    cores=1,
                    progressbar=True
                )

                self.model_trained = True
                print(f"模型训练完成，采样 {samples} 次，预热 {tune} 次")

                # 保存参数后验分布
                stutter_mean_post = self.trace.posterior['stutter_mean'].mean()
                stutter_sigma_post = self.trace.posterior['stutter_sigma'].mean()
                print(f"脱扣峰分布: μ={stutter_mean_post:.4f}, σ={stutter_sigma_post:.4f}")

                return self.trace

        except Exception as e:
            print(f"模型训练失败: {e}")
            print("使用阈值方法代替")
            self.model_trained = False
            return None

    def denoise_new_data(self, new_noisy_df):
        """
        使用训练好的模型对新数据进行降噪
        """
        if new_noisy_df.empty:
            print("警告: 新数据为空")
            return pd.DataFrame()

        print("使用脱扣峰检测方法降噪")

        # 预处理数据
        processed_df = self.preprocess_noisy_data(new_noisy_df.copy())

        # 应用脱扣峰过滤
        denoised_df = self.apply_stutter_filter(processed_df)

        # 处理低峰高信号
        denoised_df = self.handle_low_peak_height(denoised_df)

        # 保留有效信号
        denoised_df = denoised_df[~denoised_df['IsStutter']].copy()

        # 输出结果
        signal_count = len(denoised_df)
        print(f"降噪后保留 {signal_count} 个信号点")
        return denoised_df

    def apply_stutter_filter(self, df):
        """
        应用脱扣峰过滤
        """
        if df.empty or 'HeightRatio' not in df.columns:
            return df

        print("应用脱扣峰过滤...")

        # 使用训练好的模型参数或提取的统计信息
        if self.model_trained and self.trace is not None:
            print("使用训练模型参数进行脱扣峰检测")
            stutter_mean = self.trace.posterior['stutter_mean'].mean()
            stutter_sigma = self.trace.posterior['stutter_sigma'].mean()
            threshold = stutter_mean + 2 * stutter_sigma
        else:
            print("使用提取的脱扣峰统计信息")
            stutter_stats = self.prior_knowledge.get('stutter_stats', self._get_default_stutter_stats())

            # 创建脱扣统计字典
            stutter_dict = {}
            if not stutter_stats.empty:
                for _, row in stutter_stats.iterrows():
                    key = (row['Marker'], row['Dye'])
                    stutter_dict[key] = (row['MeanRatio'], row['StdRatio'])

        # 对每个样本和标记进行处理
        changed_count = 0
        for (sample, marker), group in df.groupby(['Sample', 'Marker']):
            if len(group) < 2:
                continue

            # 获取染料
            dye = group['Dye'].iloc[0] if 'Dye' in group.columns else 'B'

            # 获取脱扣参数
            if self.model_trained:
                stutter_threshold = threshold
            else:
                stutter_key = (marker, dye)
                if stutter_key in stutter_dict:
                    stutter_mean, stutter_std = stutter_dict[stutter_key]
                    stutter_threshold = stutter_mean + 2 * stutter_std
                else:
                    stutter_threshold = 0.3  # 默认阈值
                    print(f"警告: 无{marker}-{dye}的脱扣峰统计，使用默认阈值{stutter_threshold}")

            # 找出主峰（高度最大）
            main_peak_idx = group['Height'].idxmax()
            main_allele = group.loc[main_peak_idx, 'Allele']
            main_height = group.loc[main_peak_idx, 'Height']

            for idx, row in group.iterrows():
                if idx == main_peak_idx:
                    continue  # 跳过主峰

                allele_diff = abs(row['Allele'] - main_allele)
                height_ratio = row['Height'] / main_height

                # 检查是否符合脱扣峰特征
                if (0.5 <= allele_diff <= 5.0 and
                        height_ratio <= stutter_threshold):
                    df.loc[idx, 'IsStutter'] = True
                    changed_count += 1

        print(f"识别出 {changed_count} 个脱扣峰")
        return df

    def handle_low_peak_height(self, df):
        """
        处理低峰高信号
        """
        if df.empty:
            return df

        print("处理低峰高信号...")

        df = df.copy()
        global_min_threshold = self.thresholds['global_min']

        # 识别低峰高信号
        df['IsLowPeak'] = df['Height'] < global_min_threshold
        low_peak_count = df['IsLowPeak'].sum()
        print(f"低峰高信号数量: {low_peak_count}")

        # 对每个样本和标记进行处理
        for (sample, marker), group in df.groupby(['Sample', 'Marker']):
            if group.empty:
                continue

            # 检查是否有非低峰高的有效信号
            has_high_peak = any(group['IsStutter'] & ~group['IsLowPeak'])

            if not has_high_peak and any(group['IsStutter']):
                # 无高可信度峰，保留最强峰
                # 只考虑当前标记的信号点
                candidate_group = group[~group['IsStutter']]
                if not candidate_group.empty:
                    strongest_idx = candidate_group['Height'].idxmax()
                    # 确保该峰没有被其他规则过滤掉
                    df.loc[strongest_idx, 'IsStutter'] = False

        # 移除临时列
        if 'IsLowPeak' in df.columns:
            df = df.drop(columns=['IsLowPeak'])

        return df

    def visualize_results(self, sample_name, marker_name, df):
        """
        可视化降噪结果
        """
        if df.empty:
            print("无法可视化: 数据为空")
            return

        sample_data = df[(df['Sample'] == sample_name) & (df['Marker'] == marker_name)]
        if sample_data.empty:
            print(f"未找到匹配数据: {sample_name} - {marker_name}")
            return

        print(f"为 {sample_name} - {marker_name} 可视化结果...")

        # 准备绘图数据
        heights = sample_data['Height'].values
        alleles = sample_data['Allele'].values if 'Allele' in sample_data.columns else np.arange(len(sample_data))
        signals = sample_data['IsStutter'].values if 'IsStutter' in sample_data.columns else [False] * len(sample_data)

        # 创建图表
        plt.figure(figsize=(12, 8))

        # 绘制结果
        positions = np.arange(len(heights))
        colors = ['red' if s else 'green' for s in signals]

        plt.bar(positions, heights, color=colors, alpha=0.7)

        # 标注等位基因和高度
        for i, (height, allele) in enumerate(zip(heights, alleles)):
            plt.text(i, height + max(heights) * 0.05, f"{allele:.1f}",
                     ha='center', fontsize=9)

        # 添加图例
        plt.title(f'降噪结果: {sample_name} - {marker_name}')
        plt.xlabel('峰索引')
        plt.ylabel('高度 (RFU)')
        plt.legend(handles=[
            plt.Rectangle((0, 0), 1, 1, color='green'),
            plt.Rectangle((0, 0), 1, 1, color='red')
        ], labels=['保留信号', '脱扣峰'])

        plt.tight_layout()

        # 创建文件名
        safe_sample = re.sub(r'[\\/*?:"<>|]', "_", sample_name)
        safe_marker = re.sub(r'[\\/*?:"<>|]', "_", marker_name)
        filename = f'denoise_{safe_sample}_{safe_marker}.png'

        plt.savefig(filename)
        print(f"结果图已保存至 {filename}")
        plt.close()


def interactive_mode():
    """
    交互式模式，引导用户完成降噪过程
    """
    print("\n" + "=" * 50)
    print("贝叶斯STR数据降噪系统 - 交互模式")
    print("=" * 50)
    print("此系统使用贝叶斯方法检测和去除STR数据中的脱扣峰噪声")
    print("第一步: 模型训练过程")
    print("第二步: 降噪处理循环 (输入'exit'退出)\n")

    # 1. 获取噪声数据路径
    noisy_data_path = ""
    while not noisy_data_path:
        print("\n" + "-" * 60)
        print("步骤 1/5: 输入噪声数据文件路径")
        print("提示: 文件应为Excel格式，包含Sample、Marker、Dye及多个Allele/Size/Height列")
        print("默认文件: '附件1：不同人数的STR图谱数据.xlsx'")

        user_input = input("请提供噪声数据文件路径 (或直接回车使用默认文件): ").strip()
        if user_input:
            if os.path.exists(user_input):
                noisy_data_path = user_input
            else:
                print(f"警告: 文件不存在 - {user_input}")
                print("请重新输入或使用默认文件")
                continue
        else:
            # 使用默认文件
            if os.path.exists(NOISY_DATA_PATH):
                noisy_data_path = NOISY_DATA_PATH
                print(f"使用默认噪声数据文件: {noisy_data_path}")
            else:
                print("错误: 默认噪声数据文件不存在")

    if not noisy_data_path:
        print("错误: 无法获取噪声数据文件，退出系统")
        return

    # 2. 获取降噪后数据路径 (可选)
    denoised_data_path = ""
    print("\n" + "-" * 60)
    print("步骤 2/5: 提供降噪后数据文件路径 (可选)")
    print("提示: 如果您有已知的降噪后数据，可以提供以提升模型准确性")
    print("默认文件: '附件4：去噪后的STR图谱数据.xlsx'")

    user_input = input("请提供降噪后数据文件路径 (或直接回车跳过此步骤): ").strip()
    if user_input:
        if os.path.exists(user_input):
            denoised_data_path = user_input
        else:
            print(f"警告: 文件不存在 - {user_input}")
            print("将跳过此步骤")
    elif os.path.exists(DENOISED_DATA_PATH):
        denoised_data_path = DENOISED_DATA_PATH
        print(f"使用默认降噪后数据文件: {denoised_data_path}")

    # 3. 初始化降噪器
    print("\n" + "-" * 60)
    print("步骤 3/5: 初始化降噪器")
    try:
        print("正在初始化降噪器，请稍候...")
        denoiser = BayesianSTRDenoiser(noisy_data_path, denoised_data_path)
        print("降噪器初始化成功!")

        # 显示数据统计信息
        height_stats = denoiser.get_height_stats()
        if height_stats is not None:
            print("\n噪声数据高度统计:")
            print(f"峰值数量: {len(denoiser.noisy_data)}")
            print(f"最小高度: {height_stats['min']:.2f} RFU")
            print(f"平均高度: {height_stats['mean']:.2f} RFU")
            print(f"最大高度: {height_stats['max']:.2f} RFU")
            print(f"使用的阈值: 全局最小值={denoiser.thresholds['global_min']} RFU")
    except Exception as e:
        print(f"初始化失败: {e}")
        print("请检查输入文件格式是否正确")
        return

    # 4. 提取先验知识和训练模型
    print("\n" + "-" * 60)
    print("步骤 4/5: 准备脱扣峰检测模型")
    try:
        prior_knowledge = denoiser.extract_prior_knowledge()
        if 'stutter_stats' in prior_knowledge:
            stutter_stats = prior_knowledge['stutter_stats']
            print(f"\n提取到脱扣峰统计数据: {len(stutter_stats)} 个位点")
            print(f"平均脱扣比率: {stutter_stats['MeanRatio'].mean():.4f} ± {stutter_stats['StdRatio'].mean():.4f}")

            # 显示部分脱扣统计信息
            print("\n部分位点脱扣峰统计:")
            print(stutter_stats.head(5))

            if len(stutter_stats) < 5:
                print("\n警告: 提取到的脱扣峰数据较少，可能会影响模型准确性")

        # 训练模型
        print("\n开始训练脱扣峰检测模型...")
        use_model = input("是否使用贝极斯模型? (是/否) [默认:是]: ").strip().lower()
        if use_model in ['', 'y', 'yes', '是']:
            samples = 1000
            tune = 500
            try:
                user_samples = input(f"输入采样次数 (默认={samples}): ").strip()
                if user_samples:
                    samples = max(100, min(5000, int(user_samples)))

                user_tune = input(f"输入预热次数 (默认={tune}): ").strip()
                if user_tune:
                    tune = max(100, min(2000, int(user_tune)))

                print("\n开始训练模型，这可能需要几分钟...")
                denoiser.train_model(samples, tune)
                print(f"模型训练完成! 采样 {samples} 次，预热 {tune} 次")

                # 保存模型训练摘要
                if denoiser.model_trained and denoiser.trace is not None:
                    pm.summary(denoiser.trace).to_csv("模型训练摘要.csv")
                    print("模型训练摘要已保存为 '模型训练摘要.csv'")
            except Exception as e:
                print(f"模型训练失败: {e}")
                print("将使用阈值方法进行脱扣峰检测")
        else:
            print("跳过模型训练，将使用阈值方法")
    except Exception as e:
        print(f"处理脱扣峰信息失败: {e}")
        return

    # 5. 进入降噪处理循环
    print("\n" + "=" * 60)
    print("模型训练已完成，现在您可以进行降噪处理")
    print("支持方式: 1)处理文件数据 2)手动输入数据")
    print("注意: 输入'exit'可以随时退出系统")
    print("=" * 60)

    while True:
        print("\n" + "=" * 60)
        print("降噪处理菜单")
        print("1. 处理文件数据 (Excel格式)")
        print("2. 手动输入数据进行降噪")
        print("3. 重新处理原始噪声数据")
        print("4. 查看模型信息")
        print("5. 退出系统")
        print("=" * 60)

        choice = input("\n请输入选项 [默认:1]: ").strip()

        if choice == "3":
            # 使用原始噪声数据
            if denoiser.noisy_data is None or denoiser.noisy_data.empty:
                print("错误: 原始噪声数据为空")
            else:
                print(f"\n对原始噪声数据 (共 {len(denoiser.noisy_data)} 行) 进行降噪...")
                denoised_result = denoiser.denoise_new_data(denoiser.noisy_data)

                # 保存结果
                save_and_visualize(denoiser, denoised_result, "原始噪声数据")

        elif choice == "4":
            # 显示模型信息
            print("\n当前模型信息:")
            print(f"模型训练状态: {'已训练' if denoiser.model_trained else '未训练'}")
            if denoiser.model_trained and denoiser.trace is not None:
                stutter_mean = denoiser.trace.posterior['stutter_mean'].mean().values
                stutter_sigma = denoiser.trace.posterior['stutter_sigma'].mean().values
                print(f"脱扣峰参数: 均值={stutter_mean:.4f}, 标准差={stutter_sigma:.4f}")

            if denoiser.stutter_stats is not None:
                print(f"脱扣峰统计信息: {len(denoiser.stutter_stats)} 个位点")
                print(denoiser.stutter_stats.head(3))
            else:
                print("脱扣峰统计信息: 使用默认值")

        elif choice == "5" or choice.lower() == "exit":
            print("感谢使用贝叶斯STR降噪系统!")
            break

        elif choice == "2":
            # 手动输入数据进行降噪
            process_manual_input(denoiser)

        else:
            # 处理文件数据
            print("\n" + "=" * 60)
            print("处理文件数据")
            print("请输入Excel格式的STR数据文件路径")
            print("输入'exit'返回菜单")
            print("=" * 60)

            new_data_path = ""
            while not new_data_path:
                user_input = input("\n文件路径: ").strip()

                if user_input.lower() == "exit":
                    break

                if user_input:
                    if os.path.exists(user_input):
                        new_data_path = user_input
                    else:
                        print(f"警告: 文件不存在 - {user_input}")
                        print("请重新输入有效路径")
                        continue
                else:
                    print("错误: 未提供文件路径")
                    continue

            if new_data_path:
                try:
                    print("\n加载数据并应用降噪模型...")
                    new_noisy_df = denoiser._load_data(new_data_path)
                    print(f"成功加载新数据: {len(new_noisy_df)} 行")

                    # 应用降噪
                    denoised_result = denoiser.denoise_new_data(new_noisy_df)

                    # 保存结果
                    save_and_visualize(denoiser, denoised_result, os.path.basename(new_data_path))

                except Exception as e:
                    print(f"处理文件数据失败: {e}")
                    print("请检查文件格式是否正确")
                    print(f"错误详情: {str(e)}")


def process_manual_input(denoiser):
    """
    处理手动输入数据进行降噪
    """
    print("\n" + "=" * 60)
    print("手动输入数据进行降噪")
    print("输入格式: Sample Marker Dye Allele1 Size1 Height1 [Allele2 Size2 Height2 ...]")
    print("示例: Sample001 D8S1179 B 12.0 1234.5 500.0 13.0 1237.8 150.0")
    print("注意: 所有值用空格分隔，每组等位基因包含3个值")
    print("输入'exit'返回菜单")
    print("=" * 60)

    while True:
        user_input = input("\n请输入数据 (输入'exit'返回): ").strip()

        if user_input.lower() == "exit":
            print("返回菜单")
            break

        if not user_input:
            print("错误: 未输入任何数据")
            continue

        try:
            # 解析用户输入
            parts = user_input.split()
            if len(parts) < 6 or (len(parts) - 3) % 3 != 0:
                print("错误: 输入格式不正确。需要至少6个值，后续每3个值一组。")
                print("格式: Sample Marker Dye Allele1 Size1 Height1 [Allele2 Size2 Height2 ...]")
                continue

            # 提取基础信息
            sample = parts[0]
            marker = parts[1]
            dye = parts[2]

            # 提取每个等位基因数据
            alleles = []
            sizes = []
            heights = []

            # 剩余部分(从索引3开始)应该可以被3整除
            num_points = (len(parts) - 3) // 3

            for i in range(num_points):
                start_idx = 3 + i * 3
                allele = float(parts[start_idx])
                size = float(parts[start_idx + 1])
                height = float(parts[start_idx + 2])

                alleles.append(allele)
                sizes.append(size)
                heights.append(height)

            # 创建DataFrame
            data = {
                'Sample': [sample] * num_points,
                'Marker': [marker] * num_points,
                'Dye': [dye] * num_points,
                'Allele': alleles,
                'Size': sizes,
                'Height': heights
            }

            df = pd.DataFrame(data)

            # 显示用户输入的数据
            print("\n您输入的数据:")
            print(df)

            # 应用降噪
            print("\n应用降噪算法...")
            denoised_result = denoiser.denoise_new_data(df)

            if denoised_result is None or denoised_result.empty:
                print("降噪结果为空")
            else:
                print("\n降噪结果:")

                # 简化结果输出，标记脱扣峰
                denoised_result['Status'] = np.where(
                    denoised_result['IsStutter'],
                    '[脱扣峰]',
                    '[保留信号]'
                )
                result_table = denoised_result[['Sample', 'Marker', 'Dye', 'Allele', 'Size', 'Height', 'Status']]
                print(result_table)

                # 检查脱扣峰比例
                if 'IsStutter' in denoised_result.columns:
                    stutter_count = denoised_result['IsStutter'].sum()
                    total_count = len(denoised_result)
                    stutter_percent = stutter_count / total_count * 100 if total_count > 0 else 0
                    print(f"\n检测结果: {total_count}个峰中, {stutter_count}个被标记为脱扣峰 ({stutter_percent:.1f}%)")

                # 询问是否保存结果
                save_option = input("\n是否保存降噪结果? (是/否) [默认:否]: ").strip().lower()
                if save_option in ['是', 'y', 'yes']:
                    save_path = input("输入保存路径 (默认:手动输入数据_降噪结果.xlsx): ").strip()
                    if not save_path:
                        save_path = "手动输入数据_降噪结果.xlsx"

                    denoised_result.to_excel(save_path, index=False)
                    print(f"结果已保存至: {save_path}")

                    # 询问是否立即可视化
                    visualize = input("是否立即可视化结果? (是/否) [默认:否]: ").strip().lower()
                    if visualize in ['是', 'y', 'yes']:
                        if not denoised_result.empty:
                            sample_to_visualize = sample
                            marker_to_visualize = marker
                            print(f"可视化样本: {sample_to_visualize}, 位点: {marker_to_visualize}")
                            try:
                                denoiser.visualize_results(sample_to_visualize, marker_to_visualize, denoised_result)
                                print("可视化结果已保存为PNG文件")
                            except Exception as e:
                                print(f"可视化失败: {e}")

        except Exception as e:
            print(f"数据处理失败: {e}")
            print("请确认输入格式是否正确")
            print("确保等位基因值、尺寸和高度都是数字")


def save_and_visualize(denoiser, denoised_result, data_source):
    """
    保存降噪结果并提供可视化选项
    """
    if denoised_result is None or denoised_result.empty:
        print("警告: 降噪结果为空")
        return

    # 输出结果统计
    if 'IsStutter' in denoised_result.columns:
        stutter_count = denoised_result['IsStutter'].sum()
        signal_count = len(denoised_result) - stutter_count
        print(f"\n降噪结果统计: 信号点={signal_count}, 脱扣峰={stutter_count}")
    else:
        print(f"降噪结果包含 {len(denoised_result)} 个数据点")

    # 保存结果
    output_path = ""
    while not output_path:
        default_output = f"脱扣峰降噪结果_{data_source}.xlsx"
        user_input = input(f"\n请输入结果保存路径 (或回车使用默认: {default_output}): ").strip()

        if user_input.lower() == "exit":
            print("已取消保存")
            return

        if not user_input:
            output_path = default_output
        else:
            # 确保文件扩展名正确
            if not user_input.lower().endswith(('.xlsx', '.xls')):
                user_input += '.xlsx'
            output_path = user_input

    try:
        denoised_result.to_excel(output_path, index=False)
        print(f"\n降噪结果已保存至: {output_path}")

        # 计算降噪率
        if denoiser.noisy_data is not None:
            reduction_rate = 100 * (1 - len(denoised_result) / len(denoiser.noisy_data))
            print(f"数据点减少率: {reduction_rate:.1f}%")
    except Exception as e:
        print(f"保存结果失败: {e}")
        return

    # 可视化选项
    if denoised_result.empty:
        return

    visualize = input("\n是否可视化降噪结果? (是/否) [默认:否]: ").strip().lower()

    if visualize in ['是', 'y', 'yes']:
        # 随机选择一个样本和位点
        print("\n随机选择一个样本和位点进行可视化...")
        samples = denoised_result['Sample'].unique()
        if not samples.size:
            print("没有可用样本")
            return

        sample_to_visualize = np.random.choice(samples)
        markers = denoised_result[denoised_result['Sample'] == sample_to_visualize]['Marker'].unique()
        if not markers.size:
            print(f"样本 {sample_to_visualize} 没有可用位点")
            return

        marker_to_visualize = np.random.choice(markers)

        print(f"可视化样本: {sample_to_visualize}, 位点: {marker_to_visualize}")
        try:
            denoiser.visualize_results(sample_to_visualize, marker_to_visualize, denoised_result)
            print("可视化结果已保存为PNG文件")
        except Exception as e:
            print(f"可视化失败: {e}")


# 主程序入口
if __name__ == "__main__":
    print("贝叶斯STR降噪系统")
    print("=" * 50)
    print("请选择运行模式:")
    print("1. 交互模式 (模型训练+多次处理)")
    print("2. 批量模式 (使用默认参数快速运行)")
    print("输入'exit'退出系统\n")

    while True:
        mode_choice = input("请输入选项 [默认:1]: ").strip()

        if mode_choice.lower() == "exit":
            print("已退出系统")
            break

        if mode_choice == "2":
            print("\n" + "=" * 50)
            print("贝叶斯STR降噪系统 - 批量模式")
            print("=" * 50)

            try:
                # 1. 初始化降噪器
                print("\n初始化降噪器...")
                denoiser = BayesianSTRDenoiser(NOISY_DATA_PATH, DENOISED_DATA_PATH)

                # 2. 提取先验知识
                print("提取脱扣峰统计信息...")
                denoiser.extract_prior_knowledge()

                # 3. 训练模型
                print("训练模型...")
                denoiser.train_model(samples=800, tune=300)

                # 4. 应用降噪
                print("应用降噪算法...")
                denoised_result = denoiser.denoise_new_data(denoiser.noisy_data)

                # 5. 保存结果
                if not denoised_result.empty:
                    output_path = "脱扣峰降噪结果_批量模式.xlsx"
                    denoised_result.to_excel(output_path, index=False)
                    print(f"\n降噪结果已保存至 {output_path}")

                    # 可选: 随机可视化一个结果
                    samples = denoised_result['Sample'].unique()
                    markers = denoised_result['Marker'].unique()

                    if samples.size and markers.size:
                        sample_to_visualize = np.random.choice(samples)
                        sample_markers = denoised_result[denoised_result['Sample'] == sample_to_visualize][
                            'Marker'].unique()
                        if sample_markers.size:
                            marker_to_visualize = np.random.choice(sample_markers)
                            print(f"\n随机可视化: {sample_to_visualize} - {marker_to_visualize}")
                            denoiser.visualize_results(sample_to_visualize, marker_to_visualize, denoised_result)

            except Exception as e:
                print(f"\n批量模式运行失败: {e}")

            print("\n批量处理完成! 感谢使用贝叶斯STR降噪系统")
            break

        else:
            # 默认运行交互模式
            interactive_mode()
            print("\n感谢使用贝叶斯STR降噪系统")
            break

    print("\n程序已结束")
