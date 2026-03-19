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
from sklearn.metrics import accuracy_score, precision_score, recall_score

# 1. 导入数据集
file_path = '附件_处理后10.xlsx'

try:
    excel_file = pd.ExcelFile(file_path)
    df = excel_file.parse('女胎检测数据')
    print(f"成功导入数据，共 {df.shape[0]} 行，{df.shape[1]} 列")
except FileNotFoundError:
    print(f"错误：找不到文件 '{file_path}'")
    exit()
except Exception as e:
    print(f"读取数据错误：{str(e)}")
    exit()


# 2. 数据预处理 - 染色体异常解析
def parse_chromosome_abnormal(code):
    code_str = str(int(code))
    return {
        '13号染色体非整倍体': 1 if '1' in code_str else 0,
        '18号染色体非整倍体': 1 if '2' in code_str else 0,
        '21号染色体非整倍体': 1 if '3' in code_str else 0
    }


abnormal_features = df['染色体的非整倍体'].apply(parse_chromosome_abnormal).apply(pd.Series)
df = pd.concat([df, abnormal_features], axis=1)

# 3. 特征工程 - 强化21号染色体特征（基于原有特征）
core_z_features = ['13号染色体的Z值', '18号染色体的Z值', '21号染色体的Z值']
aux_features = [
    '孕妇BMI', 'X染色体浓度',
    '13号染色体的GC含量', '18号染色体的GC含量', '21号染色体的GC含量',
    '被过滤掉读段数的比例',
    '13号染色体非整倍体', '18号染色体非整倍体', '21号染色体非整倍体'
]
features = core_z_features + aux_features

X = df[features].copy()

# 临床优先级加权 - 提高21号染色体Z值权重
clinical_weights = {
    '21号染色体的Z值': 15.0,
    '18号染色体的Z值': 6.0,
    '13号染色体的Z值': 5.0,
    '孕妇BMI': 0.5,
    'X染色体浓度': 0.5,
    '13号染色体的GC含量': 0.3,
    '18号染色体的GC含量': 0.3,
    '21号染色体的GC含量': 0.3,
    '被过滤掉读段数的比例': 0.3,
    '13号染色体非整倍体': 0.4,
    '18号染色体非整倍体': 0.4,
    '21号染色体非整倍体': 0.4
}

X_weighted = X.copy()
for feature, weight in clinical_weights.items():
    X_weighted[feature] = X_weighted[feature] * weight

# 4. 数据预处理管道
preprocessor = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

X_processed = preprocessor.fit_transform(X_weighted)
X_processed_df = pd.DataFrame(X_processed, columns=features, index=X.index)

# 5. 异常检测模型
models = {
    '椭圆包络': EllipticEnvelope(contamination=0.05, random_state=42),
    '隔离森林': IsolationForest(
        contamination=0.05,
        n_estimators=100,
        max_samples='auto',
        random_state=42
    ),
    '局部离群因子': LocalOutlierFactor(
        n_neighbors=15,
        contamination=0.05,
        novelty=True
    )
}

results = df.copy()
for name, model in models.items():
    model.fit(X_processed)
    results[f'{name}_异常标签'] = model.predict(X_processed)
    if name == '局部离群因子':
        results[f'{name}_异常分数'] = -model.decision_function(X_processed)
    else:
        results[f'{name}_异常分数'] = model.decision_function(X_processed)


# 6. 综合异常判定 - 21号染色体优先
def calculate_anomaly_probability(row):
    # 21号染色体Z值优先判定
    if abs(row['21号染色体的Z值']) > 2.0:
        return 100.0
    elif 1.5 < abs(row['21号染色体的Z值']) <= 2.0:
        return 95.0
    elif abs(row['18号染色体的Z值']) > 3.0:
        return 90.0
    elif abs(row['13号染色体的Z值']) > 3.0:
        return 80.0
    else:
        anomaly_flags = [
            row['椭圆包络_异常标签'] == -1,
            row['隔离森林_异常标签'] == -1,
            row['局部离群因子_异常标签'] == -1
        ]
        base_prob = sum(anomaly_flags) / len(anomaly_flags) * 100
        return base_prob


results['综合异常概率(%)'] = results.apply(calculate_anomaly_probability, axis=1)
results['是否建议进一步检查'] = results['综合异常概率(%)'] > 60.0

# 7. 数据格式化处理
float_columns = results.select_dtypes(include=['float']).columns.tolist()
for col in float_columns:
    if col != '综合异常概率(%)':
        results[col] = results[col].apply(lambda x: f'{x:.4f}')
results['综合异常概率(%)'] = results['综合异常概率(%)'].apply(lambda x: f'{x:.2f}')
unnamed_cols = [col for col in results.columns if 'unnamed' in col.lower()]
results = results.drop(unnamed_cols, axis=1)

# 8. 模型训练与评估 + 优化饼状图
y = results['是否建议进一步检查'].astype(int)
# 分层抽样确保21号染色体相关样本分布合理
stratify_col = df['21号染色体非整倍体'].astype(str) + "_" + y.astype(str)
X_train, X_test, y_train, y_test = train_test_split(
    X_processed_df,
    y,
    test_size=0.2,
    random_state=42,
    stratify=stratify_col
)

# 调整随机森林参数，增强对21号染色体特征的学习
rf = RandomForestClassifier(
    n_estimators=200,  # 增加树的数量，提升学习能力
    max_depth=6,  # 较浅深度，防止过拟合其他特征
    min_samples_split=5,  # 降低分裂阈值，更容易基于21号特征分裂
    min_samples_leaf=1,
    class_weight='balanced',
    random_state=42,
    max_features='sqrt'  # 限制每次分裂的特征数量，增加21号特征被选中概率
)
rf.fit(X_train, y_train)

# 特征重要性
importance = pd.DataFrame({
    '特征': features,
    '重要性': rf.feature_importances_
}).sort_values('重要性', ascending=False)

print("\n特征重要性排名（临床优先级：21号Z值 > 18号Z值 > 13号Z值）:")
print(importance)

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 定义颜色列表
colors = [
    '#8FD3E8', '#FFFACD', '#C9CCD5', '#E9D8A6', '#BBE1FA',
    '#94B49F', '#B5E48C', '#FFD7BA', '#A3C4F3', '#F7CACA',
    '#C4F1C4', '#FDE74C'
]

# 绘制饼状图（优化布局）
plt.figure(figsize=(14, 8))  # 增大画布宽度
filtered_importance = importance[importance['重要性'] > 0.01]

# 提取特征名称和对应颜色，用于图例
feature_names = filtered_importance['特征'].tolist()
feature_colors = colors[:len(feature_names)]

# 绘制饼图，不显示标签（标签将在图例中显示）
wedges, texts, autotexts = plt.pie(
    filtered_importance['重要性'],
    autopct='%1.1f%%',  # 只显示百分比
    startangle=90,
    colors=feature_colors,
    pctdistance=0.85,  # 百分比位置
    wedgeprops=dict(width=0.7)  # 使用稍窄的饼图，增加空间
)

# 调整百分比文本
for autotext in autotexts:
    autotext.set_fontsize(10)
    autotext.set_color('white')
    autotext.set_weight('bold')

# 添加图例，放在右侧，解决标签拥挤问题
plt.legend(
    feature_names,
    title="特征名称",
    loc="center left",
    bbox_to_anchor=(1, 0.5),  # 图例位置在图表右侧中间
    fontsize=10,
    title_fontsize=12
)

plt.title('特征重要性占比饼状图', fontsize=14, pad=20)
plt.axis('equal')
plt.tight_layout()
plt.subplots_adjust(right=0.75)  # 调整右侧边距，为图例留出空间
plt.show()

# 模型性能
y_pred = rf.predict(X_test)
print("\n模型整体性能评估:")
print(f"准确率: {accuracy_score(y_test, y_pred):.4f}")
print(f"精确率: {precision_score(y_test, y_pred):.4f}")
print(f"召回率: {recall_score(y_test, y_pred):.4f}")

# 9. 保存结果
output_path = '女胎异常检测结果_21号强化版.xlsx'
results.to_excel(output_path, index=False)
print(f"\n结果已保存至: {output_path}")
