import pandas as pd
import re

def extract_contributor_numbers(sample_name):
    """
    从样本名称中提取贡献者编号并格式化为5列
    格式示例：B01_RD14-0003-44_45-1;1-M2S30-0.25IP-Q3.0_002.5sec.fsa
    """
    # 使用正则表达式匹配贡献者编号部分
    match = re.search(r'RD14-0003-([\d_]+)', sample_name)
    if not match:
        return ['0'] * 5  # 如果未找到匹配，返回5个0

    contributors_str = match.group(1)
    # 分割贡献者编号
    contributors = contributors_str.split('_')

    # 格式化为5列（空缺补0）
    result = contributors[:5]  # 最多取5个编号
    return result + ['0'] * (5 - len(result))  # 不足5个补0


# 读取Excel文件
file_path = '附件1：不同人数的STR图谱数据.xlsx'
df = pd.read_excel(file_path, sheet_name='sheet1')

# 处理第一列数据，提取贡献者编号
contributors_data = df.iloc[:, 0].apply(extract_contributor_numbers)

# 创建新的DataFrame存储贡献者编号
contributors_df = pd.DataFrame(
    contributors_data.tolist(),
    columns=['contributor1', 'contributor2', 'contributor3', 'contributor4', 'contributor5']
)

# 移除原始的第一列（Sample File列）
df = df.drop(df.columns[0], axis=1)

# 合并数据：贡献者编号 + 原始数据
result_df = pd.concat([contributors_df, df], axis=1)

# 保存处理后的数据到新文件
output_file = '提取贡献者编号后的STR数据1.xlsx'
result_df.to_excel(output_file, index=False)

print(f"处理完成！结果已保存到: {output_file}")
print(f"共处理 {len(df)} 行数据")
print(f"示例输出: {contributors_data.iloc[0] if not contributors_data.empty else '无数据'}")
# 检查转换结果


file_path = '附件2：不同混合比例的STR图谱数据.xlsx'
df = pd.read_excel(file_path, sheet_name='不同比例的数据集')

# 处理第一列数据，提取贡献者编号
contributors_data = df.iloc[:, 0].apply(extract_contributor_numbers)

# 创建新的DataFrame存储贡献者编号
contributors_df = pd.DataFrame(
    contributors_data.tolist(),
    columns=['contributor1', 'contributor2', 'contributor3', 'contributor4', 'contributor5']
)

# 移除原始的第一列（Sample File列）
df = df.drop(df.columns[0], axis=1)

# 合并数据：贡献者编号 + 原始数据
result_df = pd.concat([contributors_df, df], axis=1)

# 保存处理后的数据到新文件
output_file = '提取贡献者编号后的STR数据2.xlsx'
result_df.to_excel(output_file, index=False)

print(f"处理完成！结果已保存到: {output_file}")
print(f"共处理 {len(df)} 行数据")
print(f"示例输出: {contributors_data.iloc[0] if not contributors_data.empty else '无数据'}")
# 检查转换结果
