import pandas as pd
import numpy as np
import re
# 读取Excel文件
df = pd.read_excel('附件3：各个贡献者对应的基因型数据.xlsx', sheet_name='Sheet1')

# 步骤1: 删除第一列（Reseach ID）
df = df.drop(df.columns[0], axis=1)

# 步骤2: 重命名AM列为AWEL列
df = df.rename(columns={'AM': 'AMEL'})


# 步骤3: 处理AWEL列（X->12, Y->7）
def replace_xy(value):
    if isinstance(value, str):
        # 替换 X → 12, Y → 7，并移除空格
        replaced = value.replace('X', '12').replace('Y', '7').replace(' ', '')
        # 如果希望返回整数（如果整个字符串可以转成数字）
        try:
            return int(replaced)
        except ValueError:
            return replaced  # 如果转换失败（如包含非数字字符），返回字符串
    return value

df['AMEL'] = df['AMEL'].apply(replace_xy)

# 步骤4: 拆分所有基因座列为两列，并立即添加zygosity列
# 获取基因座列名列表（除了Sample ID）
loci_columns = [col for col in df.columns if col not in ['Sample ID']]

# 创建一个新的DataFrame来存储结果，从Sample ID开始
result_df = pd.DataFrame()
result_df['Sample ID'] = df['Sample ID']

# 对每个基因座列进行处理
for col in loci_columns:
    # 临时存储拆分后的数据
    split_data = df[col].astype(str).str.split(',', expand=True)

    # 处理拆分后的两列数据
    if split_data.shape[1] >= 2:
        # 创建新列名
        col1 = f"{col}_1"
        col2 = f"{col}_2"
        zygosity_col = f"{col}_zygosity"

        # 赋值并转换数据类型
        allele1 = split_data[0].str.strip().astype(float)
        allele2 = split_data[1].str.strip().astype(float)

        # 计算zygosity值 (0=纯合子, 1=杂合子)
        zygosity = np.where(abs(allele1 - allele2) < 1, 0, 1)

        # 将三列添加到结果DataFrame中
        result_df[col1] = allele1
        result_df[col2] = allele2
        result_df[zygosity_col] = zygosity

    else:
        print(f"警告: 列 {col} 无法拆分，保留原始数据")
        result_df[col] = df[col]

# 保存结果到新Excel文件
result_df.to_excel('转换后的基因型数据.xlsx', index=False)

print("转换完成！结果已保存到 '转换后的基因型数据.xlsx'")
print(f"最终数据包含 {len(result_df)} 行和 {len(result_df.columns)} 列")
print("列顺序: Sample ID后依次为每个基因座的三列（等位基因1, 等位基因2, 杂合子判定）")



df1 = pd.read_excel('提取贡献者编号后的STR数据1.xlsx')
df2 = pd.read_excel('提取贡献者编号后的STR数据2.xlsx')  # 替换为实际文件名

# 读取两个文件
# 检查列结构是否一致
if list(df1.columns) == list(df2.columns):
    # 垂直合并数据
    merged_df = pd.concat([df1, df2], ignore_index=True)

    # 保存到新文件
    merged_df.to_excel('合并后的基因型数据.xlsx', index=False)
    print("文件已合并到同一个工作表")
else:
    print("错误：两个文件的列结构不一致！")
    print(f"文件1的列: {df1.columns.tolist()}")
    print(f"文件2的列: {df2.columns.tolist()}")

# 读取Excel文件
file_path = '合并后的基因型数据.xlsx'
df = pd.read_excel(file_path)

# 处理Allele 1和Allele 2列
for col in ['Allele 1', 'Allele 2','Allele 3','Allele 4','Allele 5','Allele 6','Allele 7','Allele 8','Allele 9']:
    if col in df.columns:
        df[col] = df[col].apply(replace_xy)

# 保存修改后的数据（如果需要）
    df.to_excel('合并后的基因型数据.xlsx', index=False)
    print('已保存')

