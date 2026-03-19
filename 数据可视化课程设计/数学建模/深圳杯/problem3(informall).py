import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score
from sklearn.dummy import DummyClassifier
import os
import traceback

dummy_models = {}
# 定义映射关系
marker_mapping = {
    'D8S1179': 1, 'D21S11': 2, 'D7S820': 3, 'CSF1PO': 4, 'D3S1358': 5,
    'TH01': 6, 'D13S317': 7, 'D16S539': 8, 'D2S1338': 9, 'D19S433': 10,
    'vWA': 11, 'TPOX': 12, 'D18S51': 13, 'AMEL': 14, 'D5S818': 15, 'FGA': 16
}

inverse_marker_mapping = {v: k for k, v in marker_mapping.items()}

dye_mapping = {'B': 2, 'G': 7, 'Y': 4, 'R': 5, 'OL': -1}


def map_values(value):
    # 处理字符串值
    if isinstance(value, str):
        value = value.strip()  # 移除首尾空格

        # 1. 检查是否是基因座名称
        if value in marker_mapping:
            return marker_mapping[value]

        # 2. 检查是否是染料标记
        if value in dye_mapping:
            return dye_mapping[value]


# 应用函数到DataFrame的指定列
def apply_mappings(df, columns_to_map):
    """应用映射到指定列"""
    for col in columns_to_map:
        if col in df.columns:
            df[col] = df[col].apply(map_values)
    return df


# 1. 数据加载和预处理
def load_and_preprocess_data(file_path):
    """加载数据并进行预处理：OL转-1，空值转0"""
    # 读取数据
    df = pd.read_excel(file_path, header=None)

    # 预处理：将OL替换为-1，空值替换为0
    df = df.replace('OL', -1)
    df = df.fillna(0)

    return df


# 2. 数据提取和特征工程（应用映射）
def extract_features(df):
    """从数据中提取特征向量和标识向量，应用映射关系"""
    # 存储结果
    id_vectors = []
    feature_vectors = []

    # 遍历每一行数据
    for _, row in df.iloc[1:].iterrows():
        # 前5个元素作为标识向量
        id_vector = row.iloc[:5].values

        # 剩余元素作为特征向量 [marker, dye, allele1, size1, height1, ..., allele15, size15, height15]
        features = row.iloc[5:].values

        # 确保特征向量长度正确 (1 marker + 1 dye + 15*(allele+size+height) = 47)
        if len(features) < 47:
            # 不足部分用0填充
            features = np.pad(features, (0, 47 - len(features)), 'constant')
        elif len(features) > 47:
            # 截断多余部分
            features = features[:47]

        id_vectors.append(id_vector)
        feature_vectors.append(features)

    return np.array(id_vectors), np.array(feature_vectors)


# 3. 特征编码和模型训练
def train_logistic_regression(feature_vectors, target):
    """训练逻辑回归模型"""
    # 由于已经应用了映射，所有特征都是数值型的
    X = feature_vectors.astype(float)

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, target, test_size=0.2, random_state=42
    )

    # 创建并训练逻辑回归模型（带标准化）
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, multi_class='ovr')
    )
    model.fit(X_train, y_train)

    # 评估模型
    train_acc = accuracy_score(y_train, model.predict(X_train))
    test_acc = accuracy_score(y_test, model.predict(X_test))

    print(f"训练准确率: {train_acc:.4f}")
    print(f"测试准确率: {test_acc:.4f}")

    return model


# 4. 目标向量处理（新版本：每个贡献者两个等位基因值）
def process_target_vectors(id_vectors, df_genotype):
    """
    处理目标向量：将ID向量转换为基因型数据

    参数:
        id_vectors (numpy.array): 包含样本ID的向量
        df_genotype (pd.DataFrame): 基因型数据DataFrame

    返回:
        numpy.array: 目标向量数组 (10个值: 5个样本 * 2个等位基因值)
    """
    target_vectors = []

    for id_vector in id_vectors:
        # 获取样本ID列表
        sample_ids = [int(x) if x != '' and x is not None else 0 for x in id_vector]
        # 构建目标向量 (每个样本2个值: 等位基因1, 等位基因2)
        # 最多5个样本: 5 * 2 = 10
        target_vector = []

        for sample_id in sample_ids:
            # 处理无效样本
            if sample_id == 0:
                target_vector.extend([0, 0])
            else:
                # 从基因型DataFrame中提取数据
                row = df_genotype[df_genotype['Sample ID'] == sample_id].iloc[0]

                # 取两个等位基因值
                target_vector.extend([
                    row.iloc[1], row.iloc[2]  # 只取两个等位基因值
                ])

        # 确保目标向量长度为10 (5个样本 * 2)
        target_vector = np.pad(target_vector, (0, 10 - len(target_vector)), 'constant')
        target_vectors.append(target_vector)

    return np.array(target_vectors)


# 根据两个等位基因值判断状态
def determine_zygosity_status(allele1, allele2):
    """
    根据两个等位基因值判断状态:
    - 两者为0: 无贡献者
    - 绝对值差 <= 1: 纯合子
    - 绝对值差 > 7: 异常
    - 其他: 杂合子
    """
    if allele1 == 0 and allele2 == 0:
        return "无贡献者"

    # 计算绝对差
    diff = abs(allele1 - allele2)

    if diff < 1:
        return "纯合子"
    elif diff > 7:
        return "异常"
    else:
        return "杂合子"


# 交互功能（更新版：每个贡献者只有两个等位基因值）
def interactive_prediction(models, inverse_mapping):
    """交互式预测功能"""
    print("\n===== STR基因座贡献者分析交互系统 =====")
    print("系统要求输入一个包含47个数值的特征向量（逗号分隔）")
    print("格式：特征值1, 特征值2, 特征值3, ... , 特征值47")
    print("每个特征向量的结构：[基因座(数值), 染料(数值), 等位基因1, 大小1, 高度1, ...]")
    print("提示：特征向量应该包含1个基因座编号、1个染料值和15组等位基因数据（每组3个值）")
    print("\n示例输入（用于D8S1179基因座）：")
    print(
        "1,2,13,100.2,2500,14,104.5,2300,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
    print("\n输入 'exit' 退出系统，输入 'help' 查看帮助")

    while True:
        user_input = input("\n请在此处输入特征向量: ")

        # 退出条件
        if user_input.lower() in ['exit', 'quit', 'q']:
            print("感谢使用STR基因座分析系统，再见！")
            break

        # 帮助信息
        if user_input.lower() in ['help', '?', 'h']:
            print("\n输入帮助:")
            print("- 输入必须包含47个数值（逗号分隔）")
            print("- 基因座编号应在1-16之间 (1=D8S1179, 2=D21S11, 3=D7S820, ...)")
            print("- 染料编码应在2,4,5,7或-1 (2=B,7=G,4=Y,5=R,-1=OL)")
            print("- 等位基因值应该是数值（如13,14），OL标记为-1")
            print("- 示例输入中：第一个1表示基因座D8S1179，2表示染料B")
            print("- 后面的 '13,100.2,2500' 表示第一个等位基因数据（等位基因13，大小100.2，高度2500）")
            print("- 后面的 '14,104.5,2300' 表示第二个等位基因数据")
            print("- 最后40个0表示没有其他等位基因数据")
            print("- 输入 'example' 可查看示例输入")
            continue

        # 显示示例
        if user_input.lower() in ['example', 'demo', 'sample']:
            print("\n示例输入（复制粘贴即可使用）：")
            print(
                "1,2,13,100.2,2500,14,104.5,2300,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
            continue

        try:
            # 将输入字符串转换为数值列表
            feature_values = [float(x.strip()) for x in user_input.split(',') if x.strip() != '']
            original_count = len(feature_values)

            # 验证和处理输入长度
            if original_count < 47:
                # 需要补零
                padding = [0.0] * (47 - original_count)
                feature_values += padding
                print(f"注意：您输入了 {original_count} 个值，不足47个。已用0补充至47个值。")
            elif original_count > 47:
                # 需要截断
                feature_values = feature_values[:47]
                print(f"注意：您输入了 {original_count} 个值，超过47个。已截取前47个值进行处理。")
                print("提示：正确的特征向量应包含47个值。")
            else:
                print("输入值数量正确（47个），正在进行处理...")

            # 检查基因座值是否有效
            marker_value = int(feature_values[0]) if len(feature_values) >= 1 else 0
            if marker_value not in inverse_mapping and marker_value != 0:
                print(f"警告：基因座编号 {marker_value} 无效（有效范围：1-16）")
                print("系统将继续处理，但结果可能不准确。")

            # 检查染料值是否有效
            dye_value = int(feature_values[1]) if len(feature_values) >= 2 else 0
            valid_dyes = [2, 4, 5, 7, -1]
            if dye_value not in valid_dyes and dye_value != 0:
                print(f"警告：染料编码 {dye_value} 无效（有效值：2=B,7=G,4=Y,5=R,-1=OL)")
                print("系统将继续处理，但结果可能不准确。")

            # 转换为NumPy数组并重塑形状
            feature_vector = np.array(feature_values[:47]).reshape(1, -1)  # 确保长度为47

            # 预测目标向量 (前10个值: 5个样本 * 2个等位基因值)
            predictions = {}
            for dim in range(10):  # 只预测10个维度 (0-9)
                if dim in models:
                    try:
                        pred = models[dim].predict(feature_vector)
                        predictions[dim] = pred[0]
                    except Exception as e:
                        print(f"维度 {dim} 预测失败: {e}")
                        predictions[dim] = 0
                else:
                    print(f"警告：缺少维度 {dim} 的模型")
                    predictions[dim] = 0

            # 获取基因座名称
            marker_name = inverse_mapping.get(marker_value, f"未知基因座({marker_value})")

            # 获取染料名称
            dye_names = {2: "蓝色(B)", 7: "绿色(G)", 4: "黄色(Y)", 5: "红色(R)", -1: "离梯(OL)", 0: "未知染料"}
            dye_name = dye_names.get(dye_value, f"未知染料({dye_value})")

            print("\n" + "=" * 50)
            print(f"基因座分析结果: {marker_name} ({marker_value}) | 染料: {dye_name}")
            print("-" * 50)
            print("贡献者基因型分析:")
            print("-" * 50)

            # 解析5个样本的预测结果
            sample_results = []
            for sample_idx in range(5):
                # 计算目标向量中的索引位置
                allele1_idx = sample_idx * 2
                allele2_idx = sample_idx * 2 + 1

                # 获取预测值，如果缺失则使用默认值0
                allele1 = predictions.get(allele1_idx, 0)
                allele2 = predictions.get(allele2_idx, 0)

                # 确定贡献者状态
                status = determine_zygosity_status(allele1, allele2)

                # 存储结果用于显示
                sample_result = {
                    "allele1": allele1,
                    "allele2": allele2,
                    "status": status
                }
                sample_results.append(sample_result)

            # 显示结果
            for sample_idx, result in enumerate(sample_results):
                if result["status"] == "无贡献者":
                    print(f"贡献者 {sample_idx + 1}: {result['status']}")
                else:
                    print(f"贡献者 {sample_idx + 1}:")
                    print(f"  等位基因1: {result['allele1']}")
                    print(f"  等位基因2: {result['allele2']}")
                    print(f"  状态: {result['status']}")

            # 显示等位基因数据摘要
            print("\n" + "-" * 50)
            print("输入数据摘要:")
            print(f"基因座: {marker_name} | 染料: {dye_name}")
            print(f"有效等位基因组数: {sum(1 for i in range(15) if feature_values[2 + i * 3] != 0)}")

            # 显示前两组等位基因数据的细节
            for i in range(min(2, 15)):  # 显示最多前两组
                start_idx = 2 + i * 3
                if start_idx + 2 < len(feature_values):
                    allele = feature_values[start_idx]
                    size = feature_values[start_idx + 1]
                    height = feature_values[start_idx + 2]

                    # 只显示非零数据
                    if allele != 0 or size != 0 or height != 0:
                        print(f"等位基因 {i + 1}: 值={allele}, 大小={size}, 高度={height}")

            # 如果有更多数据未显示
            non_zero_count = sum(1 for i in range(15)
                                 if feature_values[2 + i * 3] != 0 or
                                 feature_values[2 + i * 3 + 1] != 0 or
                                 feature_values[2 + i * 3 + 2] != 0)

            if non_zero_count > 2:
                print(f"...还有 {non_zero_count - 2} 组等位基因数据未显示")

            print("=" * 50 + "\n")

        except ValueError:
            print("错误：输入包含非数字值，请确保只输入以逗号分隔的数字")
            print("提示：输入 'help' 查看帮助信息，或 'example' 查看示例输入")
        except Exception as e:
            print(f"处理时发生错误: {e}")
            print("请检查输入格式是否正确。输入 'help' 查看帮助信息。")


# 主程序
if __name__ == "__main__":
    # 加载并预处理数据
    # 使用示例
    # 读取Excel文件
    df = pd.read_excel("合并后的基因型数据.xlsx")

    # 定义需要映射的列（根据实际情况修改）
    columns_to_map = ["Allele 1", "Allele 2", "Allele 4", "Marker", "Dye"]

    # 应用映射
    df = apply_mappings(df, columns_to_map)

    # 保存结果（可选）
    df.to_excel("映射后的STR数据.xlsx", index=False)

    print("映射完成！")
    data_file = "映射后的STR数据.xlsx"  # 替换为实际文件路径
    genotype_file = "转换后的基因型数据.xlsx"

    df = load_and_preprocess_data(data_file)
    df_genotype = pd.read_excel(genotype_file)

    # 提取特征向量
    id_vectors, feature_vectors = extract_features(df)

    # 处理目标向量 (每个贡献者两个等位基因值)
    target_vectors = process_target_vectors(id_vectors, df_genotype)

    # 训练逻辑回归模型（每个输出维度单独训练）
    models = {}

    # 对目标向量的每个维度训练单独的模型 (10个维度: 5个样本 * 2个值)
    for i in range(target_vectors.shape[1]):
        print(f"\n训练模型输出维度 {i + 1}/{target_vectors.shape[1]}")
        model = train_logistic_regression(feature_vectors, target_vectors[:, i])
        models[i] = model

    # 示例预测
    sample_idx = 2  # 选择第二个样本
    predictions = {}

    # 对每个输出维度进行预测
    for dim in range(min(10, target_vectors.shape[1])):
        model = models.get(dim)
        if model:
            pred = model.predict(feature_vectors[sample_idx].reshape(1, -1))
            predictions[dim] = pred[0]

    print("\n样本预测结果:")
    for i in range(5):
        idx1 = i * 2
        idx2 = i * 2 + 1
        allele1 = predictions.get(idx1, 0)
        allele2 = predictions.get(idx2, 0)
        status = determine_zygosity_status(allele1, allele2)
        print(f"样本 {i + 1}: {allele1} {allele2} | 状态: {status}")

    print("\n实际标识向量:", id_vectors[sample_idx])
    print("实际特征向量:", feature_vectors[sample_idx])

    print("\n" + "=" * 50)
    print("所有准备工作完成！现在进入交互预测模式")
    print("=" * 50 + "\n")

    # 关键修复：传递 inverse_marker_mapping
    try:
        interactive_prediction(models, inverse_marker_mapping)
    except Exception as e:
        print(f"交互模式启动失败: {e}")
        traceback.print_exc()

    except Exception as e:
        print(f"程序运行出错: {e}")
        traceback.print_exc()
        print("尝试启动有限功能的交互模式...")

        # 创建虚拟模型
        for i in range(10):
            dummy_models[i] = DummyClassifier(strategy="constant", constant=i % 3)
            dummy_models[i].fit(np.zeros((1, 47)), [0])

        try:
            interactive_prediction(dummy_models, inverse_marker_mapping)
        except:
            print("无法启动交互模式，程序退出")