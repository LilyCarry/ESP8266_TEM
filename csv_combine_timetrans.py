#you know I can't speaks English well, so I describe this module as "put csv together",the function of this module is to put the csv files together, and make them into one csv file, so that we can use it to do the data analysis.
path = './csvs'
import os
import pandas as pd
# 1. 获取文件夹下所有 .csv 文件的完整路径
all_files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.csv')]
# 2. 读取所有文件并拼接（ignore_index=True 重置行号，避免索引重复）
df_combined = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)
for idx in df_combined.index:
    df_combined.at[idx,'Time'] = pd.to_datetime(df_combined.at[idx,'Time'], utc=True).tz_convert('Asia/Shanghai')
df_combined.to_csv(os.path.join(path, 'combined.csv'), index=False)  # 保存合并后的文件