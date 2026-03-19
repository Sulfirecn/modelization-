import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from scipy import stats

# 1. 数据加载与预处理
# 假设你的数据存储在 DataFrame `df` 中，并且包含以下列：
# '平均年龄', '平均身高', '平均体重', '区间中点BMI', 'Y染色体浓度', '孕周' (或其他表示时间点的字段)
df = pd.read_excel('BMI_多指标_分段平均值.xlsx')

# 2. 过滤数据：只保留Y染色体浓度在3%到5%之间的样本
df_filtered = df[(df['平均Y染色体浓度'] >= 0.03) & (df['平均Y染色体浓度'] <= 0.05)].copy()

# 3. 特征选择与加权
# 按指定权重构建特征矩阵：年龄、身高、体重各10%，BMI占70%
features = df_filtered[['平均年龄', '平均身高', '平均体重', '区间中点BMI']].copy()
weights = np.array([0.1, 0.1, 0.1, 0.7]) # 对应特征的权重
features_weighted = features * weights # 应用权重

# 4. 数据标准化（通常有利于K-Means聚类）
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features_weighted)

# 5. 确定最佳聚类数量K（使用肘部法则）
inertia = []
K_range = range(1, 11) # 测试K从1到10
for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(features_scaled)
    inertia.append(kmeans.inertia_)

# 绘制肘部法则图
plt.figure(figsize=(10, 6))
plt.plot(K_range, inertia, marker='o')
plt.xlabel('Number of clusters (K)')
plt.ylabel('Inertia')
plt.title('Elbow Method For Optimal K')
plt.grid(True)
plt.show()

# 根据肘部法则图选择合适的K值，这里假设我们选择K=3
optimal_k = 3

# 6. 使用K-Means进行聚类
kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
clusters = kmeans.fit_predict(features_scaled)
df_filtered['Cluster'] = clusters # 将聚类标签添加到过滤后的DataFrame中

# 7. 分析每个簇的特征（计算每个簇的质心）
cluster_centers_original = scaler.inverse_transform(kmeans.cluster_centers_) / weights
cluster_characteristics = pd.DataFrame(cluster_centers_original, columns=features.columns)
cluster_characteristics['Cluster_Size'] = np.bincount(clusters) # 每个簇的样本数
print("簇的特征中心（原始尺度，已去加权）:")
print(cluster_characteristics)

# 8. 寻找每个簇最适合的NIPT检测时间点
recommended_times = {}
for cluster_id in range(optimal_k):
    cluster_data = df_filtered[df_filtered['Cluster'] == cluster_id]
    # 使用中位数作为推荐时间点
    recommended_time = cluster_data['平均孕周'].median()
    recommended_times[f'Cluster_{cluster_id}'] = recommended_time

print("\n各簇推荐的NIPT检测时间点（孕周中位数）:")
print(recommended_times)

# 9.可视化聚类结果（使用前两个主成分进行降维可视化）
from sklearn.decomposition import PCA
pca = PCA(n_components=2)
features_pca = pca.fit_transform(features_scaled)

plt.figure(figsize=(10, 8))
scatter = plt.scatter(features_pca[:, 0], features_pca[:, 1], c=clusters, cmap='viridis', alpha=0.7)
plt.colorbar(scatter, label='Cluster')
plt.xlabel('Principal Component 1')
plt.ylabel('Principal Component 2')
plt.title('K-Means Clustering Results (PCA Visualization)')
for cluster_id in range(optimal_k):
    cluster_center_pca = pca.transform(kmeans.cluster_centers_[cluster_id].reshape(1, -1))
    plt.scatter(cluster_center_pca[:, 0], cluster_center_pca[:, 1], c='red', marker='x', s=200, linewidths=3)
plt.grid(True)
plt.show()

# 10. 输出最终分组结果
print("\n原始数据与聚类标签（前10行）:")
print(df_filtered[['平均年龄', '平均身高', '平均体重', '区间中点BMI', '平均Y染色体浓度', '平均孕周', 'Cluster']].head(10))