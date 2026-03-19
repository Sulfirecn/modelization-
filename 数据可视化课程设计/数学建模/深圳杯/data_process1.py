import pandas as pd
import re

#问题1
def extract_contributor_number(sample_name):
    """
    从样本名称中提取贡献者编号并计算人数
    格式示例：B01_RD14-0003-44_45-1;1-M2S30-0.25IP-Q3.0_002.5sec.fsa
    """
    # 使用正则表达式匹配贡献者编号部分
    match = re.search(r'RD14-0003-([\d_]+)', sample_name)
    if not match:
        return 0  # 如果未找到匹配，返回0

    contributors_str = match.group(1)
    # 分割贡献者编号并计算唯一人数
    contributors = set(contributors_str.split('_'))
    return len(contributors)


# 读取Excel文件
file_path = '附件1：不同人数的STR图谱数据.xlsx'
df = pd.read_excel(file_path, sheet_name='sheet1')

# 处理第一列数据
df['contributors'] = df.iloc[:, 0].apply(extract_contributor_number)

# 移除原始的第一列（Sample File列）
df = df.drop(df.columns[0], axis=1)

# 将新的contributor_number列移到第一列位置
cols = df.columns.tolist()
cols = [cols[-1]] + cols[:-1]
df = df[cols]

# 保存处理后的数据到新文件
output_file = 'processed_file1.xlsx'
df.to_excel(output_file, index=False)

print(f"处理完成！结果已保存到: {output_file}")
print(f"共处理 {len(df)} 行数据")











