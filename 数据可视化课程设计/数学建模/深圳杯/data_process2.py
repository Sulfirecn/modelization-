import pandas as pd
import re
import numpy as np


def extract_normalized_ratios(sample_name):
    """
    从样本名称中提取比例信息并归一化处理
    示例：B01_RD14-0003-44_45-1;1-M2S30-0.25IP-Q3.0_002.5sec.fsa
    提取"1;1"并转换为[0.5, 0.5]
    """
    # 匹配比例部分（分号分隔的数字序列）
    match = re.search(r'-(\d+(?:;\d+)+)-', sample_name)
    if not match:
        return [0.0] * 5  # 默认返回5个0

    # 提取比例字符串并分割
    ratio_str = match.group(1)
    ratios = ratio_str.split(';')

    # 转换为浮点数
    try:
        ratios = [float(r) for r in ratios]
    except ValueError:
        return [0.0] * 5

    # 归一化处理（确保总和为1）
    total = sum(ratios)
    if total == 0:
        normalized = [0.0] * len(ratios)
    else:
        normalized = [r / total for r in ratios]

    # 填充到5个贡献者（不足补0）
    normalized += [0.0] * (5 - len(normalized))
    return normalized[:5]  # 确保不超过5个


# 读取Excel文件
file_path = '附件2：不同混合比例的STR图谱数据.xlsx'
df = pd.read_excel(file_path, sheet_name='不同比例的数据集')

# 提取比例信息
ratios = df.iloc[:, 0].apply(extract_normalized_ratios)
ratio_columns = ['contributor_ratio_1', 'contributor_ratio_2',
                 'contributor_ratio_3', 'contributor_ratio_4',
                 'contributor_ratio_5']

# 创建比例DataFrame
ratio_df = pd.DataFrame(ratios.tolist(), columns=ratio_columns)

# 移除原始第一列
df = df.drop(df.columns[0], axis=1)

# 合并比例列和原始数据
df = pd.concat([ratio_df, df], axis=1)

# 保存处理后的数据
output_file = 'contributor_ratios_file.xlsx'
df.to_excel(output_file, index=False)

print(f"处理完成! 结果已保存到: {output_file}")
print(f"新文件列结构: {df.columns.tolist()}")
print("\n示例数据:")
print(df.head(3))


# 读取Excel文件
file_path = '附件1：不同人数的STR图谱数据.xlsx'
df = pd.read_excel(file_path, sheet_name='sheet1')

# 提取比例信息
ratios = df.iloc[:, 0].apply(extract_normalized_ratios)
ratio_columns = ['contributor_ratio_1', 'contributor_ratio_2',
                 'contributor_ratio_3', 'contributor_ratio_4',
                 'contributor_ratio_5']

# 创建比例DataFrame
ratio_df = pd.DataFrame(ratios.tolist(), columns=ratio_columns)

# 移除原始第一列
df = df.drop(df.columns[0], axis=1)

# 合并比例列和原始数据
df = pd.concat([ratio_df, df], axis=1)

# 保存处理后的数据
output_file = 'contributor_ratios_file1(3).xlsx'
df.to_excel(output_file, index=False)

print(f"处理完成! 结果已保存到: {output_file}")
print(f"新文件列结构: {df.columns.tolist()}")
print("\n示例数据:")
print(df.head(3))