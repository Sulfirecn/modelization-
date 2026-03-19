import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm


plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


# 设置Seaborn样式
sns.set_style("whitegrid")
sns.set_context("notebook", font_scale=1.2)

#数据读取
df = pd.read_excel('附件_处理后10.xlsx', sheet_name='男胎检测数据')

# 显示列名，确保与代码中的列名匹配
print("数据列名:", df.columns.tolist())

#创建图形
# 创建1行3列的子图，设置整体图像大小
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 1. 身高 vs Y染色体浓度散点图
sns.scatterplot(ax=axes[0], data=df, x='身高', y='Y染色体浓度',
                hue='年龄', palette='viridis', size='年龄',
                sizes=(20, 200), alpha=0.7)
axes[0].set_title('身高与Y染色体浓度的关系')
axes[0].set_xlabel('身高 (cm)')
axes[0].set_ylabel('Y染色体浓度')

# 2. 体重 vs Y染色体浓度散点图
sns.scatterplot(ax=axes[1], data=df, x='体重', y='Y染色体浓度',
                hue='年龄', palette='viridis', size='年龄',
                sizes=(20, 200), alpha=0.7)
axes[1].set_title('体重与Y染色体浓度的关系')
axes[1].set_xlabel('体重 (kg)')
axes[1].set_ylabel('Y染色体浓度')

# 3. 年龄 vs Y染色体浓度散点图
sns.scatterplot(ax=axes[2], data=df, x='年龄', y='Y染色体浓度',
                hue='身高', palette='coolwarm', size='体重',
                sizes=(20, 200), alpha=0.7)
axes[2].set_title('年龄与Y染色体浓度的关系')
axes[2].set_xlabel('年龄 (岁)')
axes[2].set_ylabel('Y染色体浓度')

#调整布局并显示
plt.tight_layout()
plt.show()

plt.savefig('Y染色体浓度分析.png', dpi=300, bbox_inches='tight')
print('已保存图片')