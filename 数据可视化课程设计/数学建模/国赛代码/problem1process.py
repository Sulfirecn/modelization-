import pandas as pd
import numpy as np

# 读取数据
df = pd.read_excel('附件_处理后10.xlsx')

# 筛选出BMI在28到37之间的数据
filtered_df = df[(df['孕妇BMI'] >= 28) & (df['孕妇BMI'] <= 37)].copy()

# 创建区间：从28到37，步长为0.01
bins = np.arange(28, 37.01, 0.01)

# 使用pd.cut将BMI数据分配到各个区间
filtered_df['BMI区间'] = pd.cut(filtered_df['孕妇BMI'], bins=bins, include_lowest=True)

# 按区间分组并计算每个区间的Y染色体浓度平均值和标准差[1,2,5]
result = filtered_df.groupby('BMI区间')['Y染色体浓度'].agg(['mean', 'std']).reset_index()
result.rename(columns={'mean': '平均Y染色体浓度', 'std': 'Y染色体浓度标准差'}, inplace=True)

# 计算每个区间的中点值（作为代表性BMI值）
result['区间中点BMI'] = result['BMI区间'].apply(lambda x: x.mid)

# 选择需要的列并重新排序
final_result = result[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差']]

# 导出到新的Excel文件
final_result.to_excel('BMI_Y染色体浓度_分段平均值和标准差.xlsx', index=False, engine='openpyxl')

print("处理完成！结果已保存到 'BMI_Y染色体浓度_分段平均值和标准差.xlsx'")