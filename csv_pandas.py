'''import pandas
import matplotlib.pyplot as plt
path = './csvs/'
df=pandas.read_csv(path + '06_14.csv')
df.insert(loc=0,column='时',value=df['Time'].str.slice(9,11))
df.insert(loc=1,column='分',value=df['Time'].str.slice(11,13))
df.insert(loc=2,column='秒',value=df['Time'].str.slice(13,15))
df.drop('Time',axis=1,inplace=True)
plt.rcParams['font.sans-serif'] = ['SimHei']          # 用黑体显示中文[reference:6]
plt.rcParams['axes.unicode_minus'] = False            # 解决负号显示异常
df=df.groupby(by='时').mean()
x='时';y='Temp'
plt.plot(df[x],df[y])
plt.xlabel(x);plt.ylabel(y)
plt.title('温度随时间的变化')
plt.show()
import pandas as pd
path = './csvs/'
df = pd.read_csv(path + '06_14.csv')
print(df.shape)          # 看看列数是否正常（应该是3列）
print(df.head())         # 查看前几行是否对齐
print(df.dtypes)         # Temperature 和 Humidity 应为 float64
import pandas as pd
import matplotlib.pyplot as plt

path = './csvs/'
df = pd.read_csv(path + '06_14.csv', on_bad_lines='skip')  # 跳过坏行

# 清理数值列
df['Temperature'] = pd.to_numeric(df['Temperature'], errors='coerce')
df['Humidity'] = pd.to_numeric(df['Humidity'], errors='coerce')
df.dropna(subset=['Temperature', 'Humidity'], inplace=True)

# 确保 Time 列长度正确
df = df[df['Time'].str.len() >= 16].copy()

# 提取小时
df['时'] = df['Time'].str.slice(9, 11)

# 分组聚合
grouped = df.groupby('时')['Temperature'].mean()

# 绘图
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

plt.plot(grouped.index, grouped.values)
plt.xlabel('小时')
plt.ylabel('温度 (°C)')
plt.title('温度随时间的变化')
plt.show()'''
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

path = './csvs/combined.csv'
df = pd.read_csv(path, on_bad_lines='skip')

# 清理温度列
df['Temperature'] = pd.to_numeric(df['Temperature'], errors='coerce')
df.dropna(subset=['Temperature'], inplace=True)

# 解析时间（兼容带时区）
df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
df.dropna(subset=['Time'], inplace=True)
df['Time'] = df['Time'].dt.tz_convert('Asia/Shanghai')

# 按日期分组（只取日期部分）
df['date'] = df['Time'].dt.normalize()   # 所有时间归到当天0点
daily_avg = df.groupby('date')['Temperature'].mean()

# 绘图
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(daily_avg.index, daily_avg.values, marker='o', markersize=4, linestyle='-')

# 横轴显示为 "月-日"（例如 06-18），更清晰
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
# 自动旋转
plt.xticks(rotation=45)

plt.xlabel('日期')
plt.ylabel('日均温度 (°C)')
plt.title('每日平均温度变化')
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()