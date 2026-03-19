import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')

# 1. 加载数据
try:
    df = pd.read_excel('附件_处理后10.xlsx', engine='openpyxl')
    print("数据加载成功!")
    print(f"数据框形状: {df.shape}")
    print(f"数据框列名: {df.columns.tolist()}")
except Exception as e:
    print(f"文件加载失败: {str(e)}")
    exit()

# 2. 数据探索和预处理
print("\n=== 数据探索 ===")
print(f"数据集总样本数: {len(df)}")

# 筛选出BMI在[28, 37]区间的数据
bmi_data = df[(df['孕妇BMI'] >= 28) & (df['孕妇BMI'] <= 37)].copy()
print(f"BMI在28-37之间的样本数: {len(bmi_data)}")

# 检查Y染色体浓度的分布
y_concentration = bmi_data['Y染色体浓度']
print(f"Y染色体浓度范围: [{y_concentration.min():.2f}, {y_concentration.max():.2f}]")
print(
    f"Y染色体浓度在3-5%之间的样本数: {len(bmi_data[(bmi_data['Y染色体浓度'] >= 3) & (bmi_data['Y染色体浓度'] <= 5)])}")

# 3. 创建BMI区间（以0.01为步长）
bmi_data['BMI估计值'] = bmi_data['孕妇BMI'].round(2)

# 4. 改进的特征工程
features_list = []

# 遍历每一个唯一的BMI区间值
for bmi_int in np.around(np.arange(28.00, 37.01, 0.01), decimals=2):
    # 筛选出当前BMI区间的数据
    subset = bmi_data[bmi_data['BMI估计值'] == bmi_int]

    if len(subset) == 0:
        # 如果这个BMI区间完全没有数据，跳过
        continue

    # 进一步筛选出Y染色体浓度在3%到5%之间的数据
    subset_in_range = subset[(subset['Y染色体浓度'] >= 3) & (subset['Y染色体浓度'] <= 5)]

    if len(subset_in_range) > 0:
        # 计算该区间内Y浓度在3%-5%的样本比例
        prop_in_range = len(subset_in_range) / len(subset)
        # 计算该区间内Y浓度在3%-5%的样本的平均Y浓度
        mean_y_concentration = subset_in_range['Y染色体浓度'].mean()
        # 计算该区间内Y浓度在3%-5%的样本的Y浓度标准差
        std_y_concentration = subset_in_range['Y染色体浓度'].std()
        # 计算该区间内Y浓度在3%-5%的样本的平均孕周
        mean_gestational_age = subset_in_range['检测孕周'].mean()

        features_list.append({
            'BMI估计值': bmi_int,
            '样本总数': len(subset),
            '目标范围样本数': len(subset_in_range),
            '目标范围比例': prop_in_range,
            'Y染色体浓度平均值': mean_y_concentration,
            'Y染色体浓度标准差': std_y_concentration,
            '检测孕周平均值': mean_gestational_age
        })
    else:
        # 对于没有Y浓度在3-5%数据的区间，但仍然有样本，可以计算整体特征
        prop_in_range = 0
        mean_y_concentration = subset['Y染色体浓度'].mean()
        std_y_concentration = subset['Y染色体浓度'].std()
        mean_gestational_age = subset['检测孕周'].mean()

        features_list.append({
            'BMI估计值': bmi_int,
            '样本总数': len(subset),
            '目标范围样本数': 0,
            '目标范围比例': 0,
            'Y染色体浓度平均值': mean_y_concentration,
            'Y染色体浓度标准差': std_y_concentration,
            '检测孕周平均值': mean_gestational_age
        })

# 检查是否计算出了特征
if not features_list:
    print("错误: 没有计算出任何特征。可能的原因:")
    print("1. BMI 28-37区间内没有数据")
    print("2. 所有BMI区间的Y染色体浓度都不在3-5%范围内")
    print("请检查数据是否符合要求")
    exit()

# 将特征列表转换为DataFrame
features_df = pd.DataFrame(features_list)
features_df.set_index('BMI估计值', inplace=True)

print(f"\n成功计算出 {len(features_df)} 个BMI区间的特征")

# 5. 处理缺失值
# 检查是否有缺失值
print(f"特征数据中的缺失值数量:")
print(features_df.isnull().sum())

# 使用每列的均值填充NaN值
for column in features_df.columns:
    if features_df[column].isnull().sum() > 0:
        col_mean = features_df[column].mean()
        features_df[column].fillna(col_mean, inplace=True)
        print(f"已用均值 {col_mean:.4f} 填充列 '{column}' 中的缺失值")

# 6. 选择用于聚类的特征
# 根据你的需求，选择能反映"Y浓度在3%到5%的孕期情况"的特征
feature_columns = ['目标范围比例', 'Y染色体浓度平均值', 'Y染色体浓度标准差', '检测孕周平均值']
print(f"\n用于聚类的特征: {feature_columns}")

# 7. 数据标准化[2](@ref)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(features_df[feature_columns])

# 8. 确定合适的K值（簇数）
# 使用肘部法和轮廓系数法结合[1](@ref)
sse = []
silhouette_scores = []
k_range = range(2, 11)  # 测试K从2到10

for k in k_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    sse.append(kmeans.inertia_)

    # 计算轮廓系数
    if k > 1:  # 轮廓系数需要至少2个簇
        silhouette_avg = silhouette_score(X_scaled, kmeans.labels_)
        silhouette_scores.append(silhouette_avg)
    else:
        silhouette_scores.append(0)

# 绘制手肘法图表和轮廓系数图表
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

# 手肘法图表
ax1.plot(k_range, sse, marker='o')
ax1.set_xlabel('簇数量 (K)')
ax1.set_ylabel('簇内平方误差和 (SSE)')
ax1.set_title('手肘法 - 最优K值选择')
ax1.grid(True)

# 轮廓系数图表
ax2.plot(k_range[1:], silhouette_scores[1:], marker='o', color='orange')
ax2.set_xlabel('簇数量 (K)')
ax2.set_ylabel('平均轮廓系数')
ax2.set_title('轮廓系数法 - 最优K值选择')
ax2.grid(True)

plt.tight_layout()
plt.show()

# 根据轮廓系数选择最优K值（选择轮廓系数最大的K）
if len(silhouette_scores) > 1:
    optimal_k = np.argmax(silhouette_scores[1:]) + 2  # +2是因为从K=2开始
    print(f"根据轮廓系数选择的最优K值为: {optimal_k}")
else:
    # 如果只有少量数据，使用较小的K值
    optimal_k = min(3, len(features_df) // 5)
    print(f"数据量较少，使用K值为: {optimal_k}")

# 9. 使用最优K值进行K-Means聚类
kmeans_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
cluster_labels = kmeans_final.fit_predict(X_scaled)

# 将聚类结果添加回特征DataFrame
features_df['Cluster'] = cluster_labels

# 10. 评估聚类质量
if optimal_k > 1:
    silhouette_avg = silhouette_score(X_scaled, cluster_labels)
    print(f"平均轮廓系数 (Silhouette Score) for K={optimal_k}: {silhouette_avg:.4f}")
else:
    print("K=1时无法计算轮廓系数")

# 11. 可视化结果（使用PCA进行降维）
try:
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled)

    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=cluster_labels, cmap='viridis', alpha=0.6)
    plt.xlabel('第一主成分')
    plt.ylabel('第二主成分')
    plt.title('K-means聚类结果 (PCA降维后)')
    plt.colorbar(scatter, label='簇标签')

    # 添加BMI值的标注（只标注部分点，避免过于拥挤）
    for i, (idx, row) in enumerate(features_df.iterrows()):
        if i % 10 == 0:  # 每10个点标注一个
            plt.annotate(f"{idx:.1f}", (X_pca[i, 0], X_pca[i, 1]), fontsize=8)

    plt.show()
except Exception as e:
    print(f"PCA可视化失败: {str(e)}")

# 12. 分析每个簇的特征中心（均值）
cluster_characteristics = features_df.groupby('Cluster')[feature_columns].mean()
print("\n每个簇的特征平均值：")
print(cluster_characteristics)

# 13. 输出属于同一组的BMI区间
print("\n=== 根据聚类结果分组后的BMI区间 ===")
for cluster_id in range(optimal_k):
    bmi_in_cluster = features_df.index[features_df['Cluster'] == cluster_id].values
    cluster_samples = features_df[features_df['Cluster'] == cluster_id]['样本总数'].sum()
    print(f"\n簇 {cluster_id} (包含 {len(bmi_in_cluster)} 个BMI区间, 总样本数: {cluster_samples}):")
    print(f"BMI区间: {bmi_in_cluster}")

    # 保存每个簇的BMI区间到文件
    cluster_filename = f"cluster_{cluster_id}_bmi_ranges.csv"
    pd.DataFrame(bmi_in_cluster, columns=['BMI区间']).to_csv(cluster_filename, index=False, encoding='utf-8-sig')
    print(f"已保存到文件: {cluster_filename}")

# 14. 保存所有特征和聚类结果到文件
features_df.to_csv('聚类分析结果_详细.csv', encoding='utf-8-sig')
print(f"\n详细聚类分析结果已保存到 '聚类分析结果_详细.csv'")

# 15. 简要总结
print("\n=== 分析总结 ===")
print(f"共分析了 {len(features_df)} 个BMI区间")
print(f"最佳聚类数: {optimal_k}")
print("每个簇的简要特征:")

for cluster_id in range(optimal_k):
    cluster_data = features_df[features_df['Cluster'] == cluster_id]
    print(f"\n簇 {cluster_id}:")
    print(f"  - 包含区间数: {len(cluster_data)}")
    print(f"  - 平均目标范围比例: {cluster_data['目标范围比例'].mean():.3f}")
    print(f"  - 平均Y染色体浓度: {cluster_data['Y染色体浓度平均值'].mean():.3f}")
    print(f"  - 平均检测孕周: {cluster_data['检测孕周平均值'].mean():.3f}")