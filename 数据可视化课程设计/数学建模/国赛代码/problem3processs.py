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

# 按区间分组并计算每个区间的Y染色体浓度平均值和标准差，以及年龄、身高、体重、孕周的平均值
# 主要修改点：在agg聚合函数中添加了 '孕周': 'mean'
result = filtered_df.groupby('BMI区间').agg({
    'Y染色体浓度': ['mean', 'std'],
    '年龄': 'mean',
    '身高': 'mean',
    '体重': 'mean',
    '检测孕周': 'mean'  # 新增对孕周列计算平均值
}).reset_index()

# 重命名列
result.columns = ['BMI区间', '平均Y染色体浓度', 'Y染色体浓度标准差', '平均年龄', '平均身高', '平均体重', '平均孕周']

# 计算每个区间的中点值（作为代表性BMI值）
result['区间中点BMI'] = result['BMI区间'].apply(lambda x: x.mid)


# 将 '平均孕周' 加入最终结果的列中，并调整到合适的位置
final_result = result[['区间中点BMI', '平均Y染色体浓度', 'Y染色体浓度标准差',
                      '平均年龄', '平均身高', '平均体重', '平均孕周']]

# 导出到新的Excel文件
final_result.to_excel('BMI_多指标_分段平均值.xlsx', index=False, engine='openpyxl')

print("处理完成！结果已保存到 'BMI_多指标_分段平均值.xlsx'")