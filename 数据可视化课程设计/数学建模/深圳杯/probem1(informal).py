import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
import re


# 1. 定义映射关系
marker_mapping = {
    'D8S1179': 1, 'D21S11': 2, 'D7S820': 3, 'CSF1PO': 4, 'D3S1358': 5,
    'TH01': 6, 'D13S317': 7, 'D16S539': 8, 'D2S1338': 9, 'D19S433': 10,
    'vWA': 11, 'TPOX': 12, 'D18S51': 13, 'AMEL': 14, 'D5S818': 15, 'FGA': 16
}

dye_mapping = {'B': 2, 'G': 7, 'Y': 4, 'R': 5, 'OL': -1}


# 2. 读取并预处理数据
def preprocess_data(file_path):
    # 读取Excel文件
    df = pd.read_excel(file_path, sheet_name='Sheet1')

    # 确保第一列是contributors
    if df.columns[0] != 'contributors':
        if 'contributors' in df.columns:
            cols = ['contributors'] + [col for col in df.columns if col != 'contributors']
            df = df[cols]
        else:
            df = df.rename(columns={df.columns[0]: 'contributors'})

    # 保留原始的Marker字符串值
    df['Original_Marker'] = df['Marker'].copy()

    # 替换Marker列为数值映射
    df['Marker'] = df['Marker'].map(marker_mapping).fillna(-1)

    # 替换Dye列
    df['Dye'] = df['Dye'].map(dye_mapping).fillna(-1)

    # 直接读取第一列作为贡献人数
    df['contributors'] = pd.to_numeric(df['contributors'], errors='coerce').fillna(0)

    # 只保留贡献人数为2,3,4,5的样本
    df = df[df['contributors'].between(2, 5)]

    # 转换为多分类目标变量
    df['contributors_class'] = df['contributors'].astype(int)

    # 打印贡献人数统计信息
    print("\n贡献人数统计信息:")
    print(df['contributors'].value_counts())

    return df


# 3. 特征工程 - 优化版本
def create_features(df):
    # 初始化特征矩阵和目标向量
    x = []
    y = []

    # 确保贡献人数类别列存在
    if 'contributors_class' not in df.columns:
        df['contributors_class'] = df['contributors'].astype(int)

    # 检查目标变量类别分布
    class_distribution = df['contributors_class'].value_counts()
    print(f"\n目标变量类别分布: \n{class_distribution}")

    # 遍历每一行数据
    for _, row in df.iterrows():
        features = []

        # 1. 添加Marker特征
        features.append(row['Marker'])

        # 2. 添加Dye特征
        features.append(row['Dye'])

        # 3. 只处理前15个等位基因
        heights = []
        sizes = []
        for i in range(1, 16):  # 修改为处理15个等位基因
            # 处理Allele特征
            allele_val = row.get(f'Allele {i}', 0)
            if allele_val == 'OL':
                allele_val = -1
            elif pd.isna(allele_val) or allele_val == '':
                allele_val = 0
            else:
                try:
                    allele_val = float(allele_val)
                except:
                    allele_val = 0
            features.append(allele_val)

            # 处理Size特征
            size_val = row.get(f'Size {i}', 0)
            size_val = float(size_val) if not pd.isna(size_val) else 0
            features.append(size_val)
            sizes.append(size_val)

            # 处理Height特征
            height_val = row.get(f'Height {i}', 0)
            height_val = float(height_val) if not pd.isna(height_val) else 0
            features.append(height_val)
            heights.append(height_val)

        # 添加聚合特征
        features.append(np.mean(heights) if heights else 0)
        features.append(np.max(heights) if heights else 0)
        features.append(np.mean(sizes) if sizes else 0)
        features.append(np.max(sizes) if sizes else 0)

        x.append(features)
        y.append(row['contributors_class'] - 2)  # 将类别映射为0-3（对应2-5人）

    print(f"\n特征向量维度: {len(x[0])}")
    print(f"目标变量分布: {pd.Series(y).value_counts().to_dict()}")
    return np.array(x), np.array(y)


# 4. 主函数 - 多分类逻辑回归
def main(file_path):
    # 预处理数据
    df = preprocess_data(file_path)

    # 检查数据是否足够
    if len(df) < 50:
        print(f"警告：样本量过少（{len(df)}），可能影响模型性能")

    # 创建特征矩阵和目标向量
    x, y = create_features(df)

    # 检查目标变量类别分布
    unique_classes, counts = np.unique(y, return_counts=True)
    print(f"\n目标变量唯一类别: {unique_classes}")
    print(f"各类别数量: {counts}")

    # 划分训练集和测试集
    if len(unique_classes) > 1:
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=21, stratify=y
        )
    else:
        print("警告：目标变量只有一个类别，无法分层抽样")
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=0.2, random_state=21
        )

    # 检查训练集中的类别分布
    unique_train, counts_train = np.unique(y_train, return_counts=True)
    print(f"\n训练集类别分布: {dict(zip(unique_train, counts_train))}")

    # 创建多分类逻辑回归模型
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('pca', PCA(n_components=0.95)),
        ('lr', LogisticRegression(
            max_iter=1000,
            random_state=21,
            multi_class='multinomial',  # 多分类设置
            solver='lbfgs',  # 支持多分类的求解器
            class_weight='balanced'
        ))
    ])

    try:
        # 训练模型
        pipeline.fit(x_train, y_train)

        # 评估模型
        y_pred = pipeline.predict(x_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, target_names=['2人', '3人', '4人', '5人'])

        print(f"\n模型准确率: {accuracy:.4f}")
        print("\n分类报告:")
        print(report)

        # 输出PCA分析结果
        pca = pipeline.named_steps['pca']
        print(f"\nPCA保留了 {pca.n_components_} 个主成分")
        print(f"解释了 {np.sum(pca.explained_variance_ratio_) * 100:.2f}% 的方差")

        return pipeline

    except Exception as e:
        print(f"\n训练模型时出错: {e}")
        print("尝试直接使用逻辑回归")

        model = LogisticRegression(
            max_iter=1000,
            random_state=21,
            multi_class='multinomial',
            solver='lbfgs',
            class_weight='balanced'
        )
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, target_names=['2人', '3人', '4人', '5人'])

        print(f"模型准确率: {accuracy:.4f}")
        print("\n分类报告:")
        print(report)

        return model


# 5. 解析用户输入
def parse_input(input_str):
    """解析用户输入的字符串为特征向量"""
    # 移除括号和空格
    input_str = re.sub(r'[$$$$]', '', input_str).replace(' ', '')
    items = input_str.split(',')

    # 检查输入长度
    expected_length = 1 + 1 + 15 * 3  # marker + dye + 15*(allele+size+height)
    if len(items) < expected_length:
        print(f"警告：输入长度不足{expected_length}，用0补齐")
        items += ['0'] * (expected_length - len(items))
    elif len(items) > expected_length:
        print(f"警告：输入长度超过{expected_length}，截断多余部分")
        items = items[:expected_length]

    # 解析marker和dye
    features = []

    # 处理marker
    marker_str = items[0]
    features.append(marker_mapping.get(marker_str, -1))

    # 处理dye
    dye_str = items[1]
    features.append(dye_mapping.get(dye_str, -1))

    # 处理15个等位基因
    heights = []
    sizes = []
    index = 2  # 从第3个元素开始

    for i in range(15):
        # allele
        allele_val = items[index]
        if allele_val == 'OL':
            features.append(-1)
        elif allele_val == '':
            features.append(0)
        else:
            try:
                features.append(float(allele_val))
            except:
                features.append(0)
        index += 1

        # size
        try:
            size_val = float(items[index]) if items[index] != '' else 0
        except:
            size_val = 0
        features.append(size_val)
        sizes.append(size_val)
        index += 1

        # height
        try:
            height_val = float(items[index]) if items[index] != '' else 0
        except:
            height_val = 0
        features.append(height_val)
        heights.append(height_val)
        index += 1

    # 添加聚合特征
    features.append(np.mean(heights) if heights else 0)
    features.append(np.max(heights) if heights else 0)
    features.append(np.mean(sizes) if sizes else 0)
    features.append(np.max(sizes) if sizes else 0)

    return np.array(features).reshape(1, -1)


# 6. 交互预测函数
def predict_contributors(model):
    """与用户交互，预测贡献人数"""
    print("\n请输入样本数据（格式：[marker,dye,allele1,size1,height1,...,allele15,size15,height15]）")
    print("示例：D3S1358,R,12,100,500,13,101,600,...,0,0,0")
    print("输入'exit'退出程序")

    while True:
        user_input = input("\n请输入样本数据: ")
        if user_input.lower() == 'exit':
            break

        try:
            # 解析输入
            features = parse_input(user_input)

            # 预测概率
            probabilities = model.predict_proba(features)[0]

            # 输出结果
            print("\n预测结果（贡献人数概率）:")
            for i, prob in enumerate(probabilities):
                print(f"{i + 2}人: {prob * 100:.2f}%")

            # 输出最可能的类别
            predicted_class = np.argmax(probabilities) + 2
            print(f"\n最可能的贡献人数: {predicted_class}人 (概率: {probabilities[predicted_class - 2] * 100:.2f}%)")

        except Exception as e:
            print(f"处理输入时出错: {e}")
            print("请检查输入格式是否正确")


# 7. 运行主函数
if __name__ == "__main__":
    model = main('processed_file1.xlsx')  # 替换为您的文件路径
    predict_contributors(model)