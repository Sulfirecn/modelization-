import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.decomposition import PCA
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor

# 定义映射关系
marker_mapping = {
    'D8S1179': 1, 'D21S11': 2, 'D7S820': 3, 'CSF1PO': 4, 'D3S1358': 5,
    'TH01': 6, 'D13S317': 7, 'D16S539': 8, 'D2S1338': 9, 'D19S433': 10,
    'vWA': 11, 'TPOX': 12, 'D18S51': 13, 'AMEL': 14, 'D5S818': 15, 'FGA': 16
}

dye_mapping = {'B': 2, 'G': 7, 'Y': 4, 'R': 5, 'OL': -1}


# 自定义函数处理AMEL等位基因
def map_amel_allele(value):
    if pd.isna(value) or value == '':
        return 0
    if value == 'X':
        return 12
    if value == 'Y':
        return 7
    try:
        return float(value)
    except:
        return 0


# 预处理函数 - 直接返回原始比例
def preprocess_data(file_path):
    # 读取Excel文件
    df = pd.read_excel(file_path, sheet_name='Sheet1')

    # 提取目标变量（前5列）
    target_columns = [
        'contributor_ratio_1', 'contributor_ratio_2',
        'contributor_ratio_3', 'contributor_ratio_4',
        'contributor_ratio_5'
    ]

    # 映射Marker和Dye列
    df['Marker'] = df['Marker'].map(marker_mapping).fillna(-1)
    df['Dye'] = df['Dye'].map(dye_mapping).fillna(-1)

    # 直接返回原始比例作为目标变量
    y = df[target_columns].values

    return df, y


# 特征工程函数
def create_features(df):
    # 初始化特征矩阵
    X = []

    # 遍历每一行数据
    for _, row in df.iterrows():
        features = []

        # 添加Marker和Dye特征
        features.append(row['Marker'])
        features.append(row['Dye'])

        # 处理前15对等位基因
        for i in range(1, 16):
            # 处理Allele特征
            allele_col = f'Allele {i}'
            size_col = f'Size {i}'
            height_col = f'Height {i}'

            # 特殊处理AMEL基因座
            if row['Marker'] == 14:  # AMEL
                allele_val = map_amel_allele(row.get(allele_col))
            else:
                allele_val = row.get(allele_col)
                if allele_val == 'OL':
                    allele_val = -1
                elif pd.isna(allele_val) or allele_val == '':
                    allele_val = 0
                else:
                    try:
                        allele_val = float(allele_val)
                    except:
                        allele_val = 0

            # 处理Size和Height
            size_val = row.get(size_col, 0)
            height_val = row.get(height_col, 0)

            # 添加到特征
            features.append(allele_val)
            features.append(float(size_val) if not pd.isna(size_val) else 0)
            features.append(float(height_val) if not pd.isna(height_val) else 0)

        # 添加聚合特征
        heights = []
        sizes = []
        for i in range(1, 16):
            height_val = row.get(f'Height {i}', 0)
            size_val = row.get(f'Size {i}', 0)
            if not pd.isna(height_val) and height_val != '':
                heights.append(float(height_val))
            if not pd.isna(size_val) and size_val != '':
                sizes.append(float(size_val))

        features.append(np.mean(heights) if heights else 0)
        features.append(np.max(heights) if heights else 0)
        features.append(np.mean(sizes) if sizes else 0)
        features.append(np.max(sizes) if sizes else 0)

        X.append(features)

    return np.array(X)


# 解析用户输入的函数
def parse_input(user_input):
    """解析用户输入的样本数据，提供详细的错误信息"""
    parts = [p.strip() for p in user_input.split(',')]

    # 检查输入长度
    if len(parts) < 3:
        raise ValueError("输入数据不足，至少需要Marker,Dye和一个等位基因数据")

    # 验证Marker
    marker_str = parts[0]
    if marker_str not in marker_mapping:
        valid_markers = ", ".join(marker_mapping.keys())
        raise ValueError(f"无效的Marker值: '{marker_str}'。有效值包括: {valid_markers}")
    marker = marker_mapping[marker_str]

    # 验证Dye
    dye_str = parts[1]
    if dye_str not in dye_mapping:
        valid_dyes = ", ".join(dye_mapping.keys())
        raise ValueError(f"无效的Dye值: '{dye_str}'。有效值包括: {valid_dyes}")
    dye = dye_mapping[dye_str]

    # 初始化特征向量
    features = [marker, dye]

    # 处理等位基因数据
    allele_data = parts[2:]
    num_groups = len(allele_data) // 3
    num_alleles = min(15, num_groups)

    # 检查数据完整性
    if len(allele_data) % 3 != 0:
        raise ValueError(f"等位基因数据不完整。每组等位基因需要3个值(Allele,Size,Height)，您提供了{len(allele_data)}个值")

    # 初始化高度和大小列表用于聚合特征
    heights = []
    sizes = []

    for i in range(num_alleles):
        start_idx = i * 3
        allele_val = allele_data[start_idx]
        size_val = allele_data[start_idx + 1]
        height_val = allele_data[start_idx + 2]

        # 处理AMEL基因座的特殊情况
        if marker == 14:  # AMEL
            if allele_val not in ['X', 'Y'] and not allele_val.replace('.', '', 1).isdigit():
                raise ValueError(f"第{i + 1}组等位基因: AMEL基因座只能接受X,Y或数字值，但收到: '{allele_val}'")
            allele_val = map_amel_allele(allele_val)
        else:
            if allele_val == 'OL':
                allele_val = -1
            elif allele_val == '':
                allele_val = 0
            else:
                try:
                    allele_val = float(allele_val)
                except:
                    raise ValueError(f"第{i + 1}组等位基因: 无效的Allele值: '{allele_val}'。应为数字或'OL'")

        # 处理Size值
        try:
            size_val = float(size_val) if size_val != '' else 0
        except:
            raise ValueError(f"第{i + 1}组等位基因: 无效的Size值: '{size_val}'。应为数字")

        # 处理Height值
        try:
            height_val = float(height_val) if height_val != '' else 0
        except:
            raise ValueError(f"第{i + 1}组等位基因: 无效的Height值: '{height_val}'。应为数字")

        features.append(allele_val)
        features.append(size_val)
        features.append(height_val)

        # 收集用于聚合特征
        heights.append(height_val)
        sizes.append(size_val)

    # 填充剩余的等位基因（如果有）
    remaining = 15 - num_alleles
    for _ in range(remaining):
        features.extend([0, 0, 0])  # 用0填充缺失的等位基因

    # 添加聚合特征
    features.append(np.mean(heights) if heights else 0)
    features.append(np.max(heights) if heights else 0)
    features.append(np.mean(sizes) if sizes else 0)
    features.append(np.max(sizes) if sizes else 0)

    return np.array([features])


# 交互式预测函数 - 预测贡献者具体占比
def interactive_predict(model):
    """与用户交互，预测贡献者占比"""
    print("\n" + "=" * 70)
    print(" 样本数据输入指南 ".center(70, '='))
    print("=" * 70)
    print("格式: Marker,Dye,Allele1,Size1,Height1,Allele2,Size2,Height2,...")
    print("示例: D3S1358,R,12,100,500,13,101,600")
    print("注意:")
    print("1. Marker必须是以下值之一:", ", ".join(marker_mapping.keys()))
    print("2. Dye必须是以下值之一:", ", ".join(dye_mapping.keys()))
    print("3. 每组等位基因需要3个值: Allele, Size, Height")
    print("4. 最多支持15组等位基因，不足的将自动填充为0")
    print("5. 输入'exit'退出程序")
    print("=" * 70 + "\n")

    # 提供示例输入
    examples = [
        "D3S1358,R,12,100,500,13,101,600",
        "FGA,G,22,150,800,23,151,810,24,152,820",
        "AMEL,Y,X,110,400,Y,111,410"
    ]

    print("示例输入:")
    for i, ex in enumerate(examples, 1):
        print(f"{i}. {ex}")
    print("")

    while True:
        user_input = input("请输入样本数据: ").strip()
        if user_input.lower() == 'exit':
            print("退出交互模式")
            break

        try:
            # 解析输入
            features = parse_input(user_input)

            # 预测贡献者占比
            predicted_ratios = model.predict(features)[0]

            # 确保比例非负且总和为1
            predicted_ratios = np.maximum(predicted_ratios, 0)  # 负值设为0
            total = np.sum(predicted_ratios)
            if total > 0:
                predicted_ratios /= total  # 归一化
            else:
                predicted_ratios = np.ones(5) / 5  # 如果全为0则平均分配

            # 输出结果
            print("\n" + "=" * 50)
            print(" 预测结果 - 贡献者占比 ".center(50, '-'))
            for i, ratio in enumerate(predicted_ratios, 1):
                print(f"贡献者 {i}: {ratio:.4f} ({ratio * 100:.2f}%)")

            # 解释预测结果
            print("\n解释:")
            # 根据占比解释贡献者数量
            non_zero_contributors = sum(ratio > 0.05 for ratio in predicted_ratios)  # 阈值设为5%
            if non_zero_contributors == 5:
                print("样本中所有5个贡献者都有显著贡献")
            elif non_zero_contributors >= 3:
                print(f"样本中有{non_zero_contributors}个贡献者有显著贡献")
            else:
                print(f"样本中只有{non_zero_contributors}个贡献者有显著贡献")

            # 标记主要贡献者
            main_contributors = [i for i, ratio in enumerate(predicted_ratios, 1) if ratio > 0.2]
            if main_contributors:
                print(f"主要贡献者: {', '.join(map(str, main_contributors))}")

            print("=" * 50 + "\n")

            # 提供下一步建议
            print("您可以输入另一个样本进行预测，或输入'exit'退出")

        except Exception as e:
            print("\n" + "!" * 50)
            print(" 输入错误 ".center(50, '!'))
            print(f"错误详情: {str(e)}")
            print("!" * 50)
            print("请参考输入指南修正输入，或查看上面的示例")
            print("如需帮助，请尝试输入其中一个示例\n")


# 主函数 - 使用回归模型预测具体占比
def main(file_path):
    # 预处理数据（返回原始比例作为目标变量）
    df, y = preprocess_data(file_path)

    # 创建特征矩阵
    X = create_features(df)
    print(f"特征矩阵形状: {X.shape}, 目标变量形状: {y.shape}")

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # 创建回归模型管道
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=0.95)),
        ('regressor', MultiOutputRegressor(
            Ridge(alpha=1.0, random_state=42)  # 使用岭回归
            # 也可以尝试其他回归模型：
            # RandomForestRegressor(n_estimators=100, random_state=42)
            # MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)
        ))
    ])

    # 训练模型
    pipeline.fit(X_train, y_train)

    # 评估模型
    y_pred = pipeline.predict(X_test)

    # 计算评估指标
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("\n回归模型评估:")
    print(f"均方误差(MSE): {mse:.4f}")
    print(f"决定系数(R²): {r2:.4f}")

    # 输出PCA分析结果
    pca = pipeline.named_steps['pca']
    print(f"\nPCA保留了 {pca.n_components_} 个主成分")
    print(f"解释了 {np.sum(pca.explained_variance_ratio_) * 100:.2f}% 的方差")

    # 进入交互式预测
    interactive_predict(pipeline)

    return pipeline


# 运行主函数
if __name__ == "__main__":
    model = main('contributor_ratios_file.xlsx')