import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.neighbors import LocalOutlierFactor
from sklearn.model_selection import train_test_split

# 1. 导入数据集
file_path = '附件_处理后10.xlsx'

try:
    excel_file = pd.ExcelFile(file_path)
    df = excel_file.parse('女胎检测数据')
    print(f"成功导入数据，共 {df.shape[0]} 行，{df.shape[1]} 列")
except FileNotFoundError:
    print(f"错误：找不到文件 '{file_path}'，请检查文件路径是否正确")
    exit()
except Exception as e:
    print(f"读取数据时发生错误：{str(e)}")
    exit()


# 2. 数据预处理 - 处理染色体非整倍体特征（支持复合异常）
def parse_chromosome_abnormal(code):
    """
    解析染色体非整倍体编码：
    code: 原始编码（如0=无异常,1=13号,2=18号,3=21号,12=13+18号,13=13+21号,23=18+21号,123=三者均异常）
    返回：13号、18号、21号染色体是否异常的二元值
    """
    code_str = str(int(code))  # 转为字符串便于逐位判断
    return {
        '13号染色体非整倍体': 1 if '1' in code_str else 0,
        '18号染色体非整倍体': 1 if '2' in code_str else 0,
        '21号染色体非整倍体': 1 if '3' in code_str else 0
    }


# 应用解析函数，生成正确的特征
abnormal_features = df['染色体的非整倍体'].apply(parse_chromosome_abnormal).apply(pd.Series)
df = pd.concat([df, abnormal_features], axis=1)

# 验证复合异常样本的处理情况
print("\n复合染色体非整倍体样本处理验证：")
compound_samples = df[df['染色体的非整倍体'].isin([12, 13, 23, 123])].head(5)
print(compound_samples[['染色体的非整倍体', '13号染色体非整倍体', '18号染色体非整倍体', '21号染色体非整倍体']])

# 3. 定义特征集
features = [
    '孕妇BMI', 'X染色体浓度',
    '13号染色体的Z值', '18号染色体的Z值', '21号染色体的Z值',
    '13号染色体的GC含量', '18号染色体的GC含量', '21号染色体的GC含量',
    '被过滤掉读段数的比例',
    '13号染色体非整倍体', '18号染色体非整倍体', '21号染色体非整倍体'
]

X = df[features]

# 4. 数据预处理管道
preprocessor = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),  # 使用中位数填充缺失值，更稳健
    ('scaler', StandardScaler())  # 标准化特征
])

# 预处理数据
X_processed = preprocessor.fit_transform(X)

# 5. 配置中文显示（解决方框问题）
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC']  # 支持多种中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 6. 异常检测模型
# 初始化多个异常检测模型（多角度检测异常）
models = {
    # 基于高斯分布的异常检测
    '椭圆包络': EllipticEnvelope(contamination=0.05, random_state=42),
    # 基于隔离森林的异常检测
    '隔离森林': IsolationForest(contamination=0.05, n_estimators=100, random_state=42),
    # 基于局部离群因子的异常检测
    '局部离群因子': LocalOutlierFactor(n_neighbors=20, contamination=0.05, novelty=True)
}

# 训练模型并预测异常分数
results = df.copy()  # 保留原始数据用于结果分析

for name, model in models.items():
    # 训练模型（使用所有健康样本）
    model.fit(X_processed)

    # 预测异常标签 (-1表示异常, 1表示正常)
    results[f'{name}_异常标签'] = model.predict(X_processed)

    # 获取异常分数（分数越低越可能是异常）
    if name == '局部离群因子':
        # 局部离群因子的决策函数返回负的异常分数，取相反数使其与其他模型一致
        results[f'{name}_异常分数'] = -model.decision_function(X_processed)
    else:
        results[f'{name}_异常分数'] = model.decision_function(X_processed)


# 7. 综合异常判定
def calculate_anomaly_probability(row):
    """综合多个模型结果计算异常概率（0-100%）"""
    anomaly_flags = [
        row['椭圆包络_异常标签'] == -1,
        row['隔离森林_异常标签'] == -1,
        row['局部离群因子_异常标签'] == -1
    ]
    # 计算被多少模型判定为异常的比例
    return sum(anomaly_flags) / len(anomaly_flags) * 100


results['综合异常概率(%)'] = results.apply(calculate_anomaly_probability, axis=1)

# 设置判定阈值：当2/3以上模型判定为异常时，建议进一步检查
results['是否建议进一步检查'] = results['综合异常概率(%)'] > 66.7

# 8. 数据格式化处理
# ① 有小数的列的所有数据保留四位小数，若未满则补零
float_columns = results.select_dtypes(include=['float']).columns.tolist()
for col in float_columns:
    if col != '综合异常概率(%)':
        results[col] = results[col].apply(lambda x: f'{x:.4f}')

# ② 异常概率列中所有数据保留两位小数，若未满则补零
results['综合异常概率(%)'] = results['综合异常概率(%)'].apply(lambda x: f'{x:.2f}')

# ③ 处理空列和题头
unnamed_cols = [col for col in results.columns if 'unnamed' in col.lower()]
results = results.drop(unnamed_cols, axis=1)

# 9. 结果分析与可视化
# 显示最可能异常的前10个样本
print("\n综合异常概率最高的前10个样本:")
top_anomalies = results.sort_values('综合异常概率(%)', ascending=False).head(10)
print(top_anomalies[['孕妇代码', '检测孕周', '染色体的非整倍体', '综合异常概率(%)']])

# 可视化异常分数分布（并保存为图片）
plt.figure(figsize=(15, 5))
for i, name in enumerate(models.keys()):
    plt.subplot(1, 3, i + 1)
    try:
        n, bins, patches = plt.hist(results[f'{name}_异常分数'].astype(float), bins=30, alpha=0.7, color='#2a9d8f')
        threshold = np.median(results[f'{name}_异常分数'].astype(float))
        plt.axvline(x=threshold, color='red', linestyle='--', label=f'异常阈值: {threshold:.2f}')
    except:
        pass
    plt.title(f'{name}异常分数分布', fontsize=12)
    plt.xlabel('异常分数', fontsize=10)
    plt.ylabel('样本数', fontsize=10)
    plt.grid(axis='y', alpha=0.3)
    plt.legend()

plt.tight_layout()
image_path = '异常分数分布图.png'
plt.savefig(image_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"\n异常分数分布图已保存至: {image_path}")

# 10. 特征重要性分析
# 训练随机森林模型评估特征重要性
X_train, X_test, y_train, y_test = train_test_split(
    X_processed,
    results['是否建议进一步检查'].astype(int),
    test_size=0.2,
    random_state=42
)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# 显示特征重要性
importance = pd.DataFrame({
    '特征': features,
    '重要性': rf.feature_importances_
}).sort_values('重要性', ascending=False)

print("\n对异常判定影响最大的特征:")
print(importance)

# 11. 绘制带图例的饼状图（优化布局避免拥挤）
plt.figure(figsize=(14, 10))  # 扩大画布尺寸
filtered_importance = importance[importance['重要性'] > 0.01]  # 过滤微小特征

# 生成彩色系
colors = plt.cm.Set3(np.linspace(0, 1, len(filtered_importance)))

# 绘制饼状图，不显示标签，后续在图例中展示
wedges, texts, autotexts = plt.pie(
    filtered_importance['重要性'],
    autopct='%1.1f%%',
    startangle=90,
    colors=colors
)

# 调整百分比文本样式
for autotext in autotexts:
    autotext.set_fontsize(10)
    autotext.set_color('white')
    autotext.set_weight('bold')

# 添加图例，设置位置与示例图对应
plt.legend(
    filtered_importance['特征'],
    title='特征名称',
    loc='center left',
    bbox_to_anchor=(1, 0.5),
    fontsize=10,
    title_fontsize=12
)

plt.title('特征重要性占比饼状图', fontsize=16, pad=20)
plt.axis('equal')
plt.tight_layout()
plt.subplots_adjust(right=0.75)  # 调整右侧边距，为图例留出空间

# 保存图片
pie_image_path = '特征重要性彩色饼状图.png'
plt.savefig(pie_image_path, dpi=300, bbox_inches='tight', pad_inches=0.5)
plt.close()
print(f"\n特征重要性彩色饼状图已保存至: {pie_image_path}")

# 12. 保存完整结果
output_path = '女胎异常检测结果_完整版.xlsx'
results.to_excel(output_path, index=False)
print(f"\n所有检测结果已保存至: {output_path}")