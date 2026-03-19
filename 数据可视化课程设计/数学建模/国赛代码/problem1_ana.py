# 导入必要的库
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.diagnostic import het_white
from statsmodels.stats.stattools import durbin_watson
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# 设置中文字体支持，防止出现乱码
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

# 1. 数据加载与预处理
file_path = '附件_处理后10.xlsx'
data = pd.read_excel(file_path, sheet_name=0)  # 读取第一个工作表

# 显示数据基本信息
print("="*50)
print("数据基本信息:")
print(f"数据集形状: {data.shape}")
print("\n前5行数据:")
print(data.head())
print("\n数据列名:")
print(data.columns.tolist())
print("\n数据类型和缺失值检查:")
print(data.info())
print("\n描述性统计:")
print(data[['检测孕周', '孕妇BMI', 'Y染色体浓度']].describe())

# 提取所需数据列 
gestational_weeks = data['检测孕周']
bmi = data['孕妇BMI']
y_chromosome = data['Y染色体浓度']

# 检查并处理缺失值
if data[['检测孕周', '孕妇BMI', 'Y染色体浓度']].isnull().sum().any():
    print("\n发现缺失值，进行删除处理...")
    data = data.dropna(subset=['检测孕周', '孕妇BMI', 'Y染色体浓度'])
    gestational_weeks = data['检测孕周']
    bmi = data['孕妇BMI']
    y_chromosome = data['Y染色体浓度']

# 2. 探索性数据分析与可视化
print("\n" + "="*50)
print("进行探索性数据分析和可视化...")

# 创建综合统计图表
plt.figure(figsize=(18, 12))

# 2.1 散点图矩阵 - 展示所有变量间的关系
plt.subplot(2, 3, 1)
scatter_matrix_data = pd.DataFrame({
    '检测孕周': gestational_weeks,
    '孕妇BMI': bmi,
    'Y染色体浓度': y_chromosome
})
sns.scatterplot(data=scatter_matrix_data, x='检测孕周', y='Y染色体浓度', hue='孕妇BMI', palette='viridis', alpha=0.6)
plt.title('孕周与Y染色体浓度关系（颜色表示BMI）')
plt.grid(True, linestyle='--', alpha=0.7)

# 2.2 相关性热力图
plt.subplot(2, 3, 2)
correlation_matrix = scatter_matrix_data.corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, square=True)
plt.title('变量间相关性热力图')

# 2.3 孕周与Y染色体浓度的散点图（带趋势线）
plt.subplot(2, 3, 3)
sns.regplot(x=gestational_weeks, y=y_chromosome, scatter_kws={'alpha':0.6})
plt.title('孕周与Y染色体浓度关系（带趋势线）')
plt.xlabel('检测孕周')
plt.ylabel('Y染色体浓度')
plt.grid(True, linestyle='--', alpha=0.7)

# 2.4 BMI与Y染色体浓度的散点图（带趋势线）
plt.subplot(2, 3, 4)
sns.regplot(x=bmi, y=y_chromosome, scatter_kws={'alpha':0.6})
plt.title('BMI与Y染色体浓度关系（带趋势线）')
plt.xlabel('孕妇BMI')
plt.ylabel('Y染色体浓度')
plt.grid(True, linestyle='--', alpha=0.7)

# 2.5 Y染色体浓度的分布直方图
plt.subplot(2, 3, 5)
sns.histplot(y_chromosome, kde=True, color='skyblue')
plt.title('Y染色体浓度分布')
plt.xlabel('Y染色体浓度')
plt.ylabel('频数')
plt.grid(True, linestyle='--', alpha=0.7)

# 2.6 联合分布图 - 孕周和BMI
plt.subplot(2, 3, 6)
scatter = plt.scatter(gestational_weeks, bmi, c=y_chromosome, cmap='viridis', alpha=0.6)
plt.colorbar(scatter, label='Y染色体浓度')
plt.title('孕周与BMI关系（颜色表示Y染色体浓度）')
plt.xlabel('检测孕周')
plt.ylabel('孕妇BMI')
plt.grid(True, linestyle='--', alpha=0.7)

plt.tight_layout()
plt.savefig('探索性数据分析.png', dpi=300, bbox_inches='tight')
plt.show()

# 3. 数据准备与标准化
# 准备特征矩阵和目标变量
X = data[['检测孕周', '孕妇BMI']]
y = data['Y染色体浓度']

# 数据标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
X_scaled = pd.DataFrame(X_scaled, columns=['检测孕周_标准化', '孕妇BMI_标准化'])

# 添加常数项（截距）
X_with_const = sm.add_constant(X_scaled)

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X_with_const, y, test_size=0.2, random_state=42)

# 4. 建立多元线性回归模型
print("\n" + "="*50)
print("建立多元线性回归模型...")

# 使用statsmodels建立模型（提供更详细的统计信息）
model = sm.OLS(y_train, X_train).fit()

# 输出模型摘要
print(model.summary())

# 5. 模型诊断与检验
print("\n" + "="*50)
print("进行模型诊断与检验...")

# 5.1 多重共线性检验 - 方差膨胀因子(VIF)
vif_data = pd.DataFrame()
vif_data["特征"] = X_with_const.columns
vif_data["VIF"] = [variance_inflation_factor(X_with_const.values, i) for i in range(X_with_const.shape[1])]
print("\n方差膨胀因子(VIF):")
print(vif_data)

# 5.2 残差分析
residuals = model.resid
fitted_values = model.fittedvalues

# 绘制残差诊断图
plt.figure(figsize=(15, 10))

# 残差与拟合值图
plt.subplot(2, 3, 1)
plt.scatter(fitted_values, residuals, alpha=0.6)
plt.axhline(y=0, color='r', linestyle='--')
plt.xlabel('拟合值')
plt.ylabel('残差')
plt.title('残差与拟合值图')
plt.grid(True, linestyle='--', alpha=0.7)

# 残差Q-Q图
plt.subplot(2, 3, 2)
sm.qqplot(residuals, line='s', ax=plt.gca())
plt.title('残差Q-Q图')

# 残差直方图
plt.subplot(2, 3, 3)
sns.histplot(residuals, kde=True, color='orange')
plt.xlabel('残差')
plt.ylabel('频数')
plt.title('残差分布')

# 5.3 异方差检验 - White检验
white_test = het_white(residuals, model.model.exog)
labels = ['LM统计量', 'LM p值', 'F统计量', 'F p值']
white_result = dict(zip(labels, white_test))
print("\nWhite异方差检验结果:")
for key, value in white_result.items():
    print(f"{key}: {value:.4f}")

# 5.4 自相关检验 - Durbin-Watson检验
dw_statistic = durbin_watson(residuals)
print(f"\nDurbin-Watson统计量: {dw_statistic:.4f}")

plt.tight_layout()
plt.savefig('模型诊断图.png', dpi=300, bbox_inches='tight')
plt.show()

# 6. 结果可视化
print("\n" + "="*50)
print("创建结果可视化...")

# 6.1 创建3D回归平面图（选择两个自变量）
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')

# 绘制实际数据点
ax.scatter(X_scaled['检测孕周_标准化'], X_scaled['孕妇BMI_标准化'], y, c='blue', marker='o', alpha=0.6, label='实际数据')

# 创建网格以绘制回归平面
x_surf = np.linspace(X_scaled['检测孕周_标准化'].min(), X_scaled['检测孕周_标准化'].max(), 20)
y_surf = np.linspace(X_scaled['孕妇BMI_标准化'].min(), X_scaled['孕妇BMI_标准化'].max(), 20)
x_surf, y_surf = np.meshgrid(x_surf, y_surf)

# 计算回归平面上的预测值
exog = pd.DataFrame({
    'const': np.ones(x_surf.size),
    '检测孕周_标准化': x_surf.ravel(),
    '孕妇BMI_标准化': y_surf.ravel()
})
z_surf = model.predict(exog).values.reshape(x_surf.shape)

# 绘制回归平面
ax.plot_surface(x_surf, y_surf, z_surf, color='red', alpha=0.3, label='回归平面')

ax.set_xlabel('标准化孕周')
ax.set_ylabel('标准化BMI')
ax.set_zlabel('Y染色体浓度')
ax.set_title('多元线性回归3D可视化')
ax.legend()

plt.savefig('3D回归平面.png', dpi=300, bbox_inches='tight')
plt.show()

# 7. 模型预测与评估
print("\n" + "="*50)
print("模型预测与评估:")

# 使用测试集进行预测
y_pred = model.predict(X_test)

# 计算评估指标
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print(f"测试集评估指标:")
print(f"均方误差(MSE): {mse:.4f}")
print(f"均方根误差(RMSE): {rmse:.4f}")
print(f"平均绝对误差(MAE): {mae:.4f}")
print(f"决定系数(R²): {r2:.4f}")

# 8. 保存结果
# 将模型摘要保存到文本文件
with open('模型摘要.txt', 'w', encoding='utf-8') as f:
    f.write(str(model.summary()))

# 保存评估指标
eval_df = pd.DataFrame({
    '指标': ['MSE', 'RMSE', 'MAE', 'R²'],
    '值': [mse, rmse, mae, r2]
})
eval_df.to_excel('评估指标.xlsx', index=False)

print("\n" + "="*50)
print("分析完成！所有结果已保存到当前目录。")