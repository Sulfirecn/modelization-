import pandas as pd
import numpy as np


# 定义函数处理每个工作表
def process_sheet(df, is_female=False):
    # 删除末次月经、检测日期列
    df = df.drop(['末次月经', '检测日期'], axis=1)

    # 将检测孕周转换为具体周数
    df['检测孕周'] = df['检测孕周'].str.extract(r'(\d+)w\+?(\d+)?').fillna(0).astype(float).agg(
        lambda x: x[0] + x[1] / 7, axis=1).round(4)

    # 将胎儿是否健康中的是换成 1，否换成 0
    df['胎儿是否健康'] = df['胎儿是否健康'].map({'是': 1, '否': 0}).astype(int)

    # 处理IVF妊娠列：自然受孕换成1，IUI（人工授精）换成2，IVF（试管婴儿）换成3，确保为整数
    ivf_mapping = {
        '自然受孕': 1,
        'IUI（人工授精）': 2,
        'IVF（试管婴儿）': 3
    }
    df['IVF妊娠'] = df['IVF妊娠'].map(ivf_mapping).fillna(0).astype(int)

    # 对有小数的列保留四位小数，并补零
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].apply(lambda x: f'{x:.4f}' if pd.notnull(x) else x)

    # 处理染色体的非整倍体列：单个类型对应单个数字，多个类型连用时数字也连用
    chrom_mapping = {'T13': '1', 'T18': '2', 'T21': '3'}

    # 处理逻辑：
    # 1. 空值填充为0
    # 2. 对每个值，替换其中包含的T13/T18/T21为对应数字
    # 3. 如无匹配项则保持原内容，最后转换为整数
    def map_chromosome(value):
        if pd.isna(value):
            return 0
        # 替换每个匹配的类型为对应数字
        for key, val in chrom_mapping.items():
            value = str(value).replace(key, val)
        # 尝试转换为整数，失败则返回0
        try:
            return int(value)
        except:
            return 0

    df['染色体的非整倍体'] = df['染色体的非整倍体'].apply(map_chromosome).astype(int)

    # 将怀孕次数中≥3 换成 3，并显式指定类型为 int
    df['怀孕次数'] = df['怀孕次数'].replace('≥3', 3).astype(int)

    # 处理女胎数据中的空列
    if is_female:
        # 找出所有全为空值的列
        empty_cols = [col for col in df.columns if df[col].isna().all()]
        for col in empty_cols:
            # 将NaN替换为空字符串
            df[col] = df[col].replace(np.nan, '', regex=True)

        # 将空列的列名改为空白字符串
        new_columns = ['' if col in empty_cols else col for col in df.columns]
        df.columns = new_columns

    return df


# 读取文件
excel_file = pd.ExcelFile('附件.xlsx')

# 获取所有表名
sheet_names = excel_file.sheet_names

# 创建一个新的 Excel 文件
with pd.ExcelWriter('附件_处理后10.xlsx') as writer:
    # 遍历每个工作表
    for sheet_name in sheet_names:
        df = excel_file.parse(sheet_name)
        # 判断是否为女胎数据
        is_female = '女胎' in sheet_name
        processed_df = process_sheet(df, is_female)

        # 将处理后的数据写入新的 Excel 文件
        processed_df.to_excel(writer, sheet_name=sheet_name, index=False)
    print('数据预处理完成')
