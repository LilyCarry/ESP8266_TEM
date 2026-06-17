from flask import Flask, request
import csv
from datetime import datetime
import os

app = Flask(__name__)
CSV_FILE = "sensor_data.csv"

# 如果 CSV 文件不存在，先初始化表头
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Temperature (C)", "Humidity (%)"])

# 监听 ESP8266 访问的路径
@app.route('/your_endpoint', methods=['GET'])
def receive_data():
    # 提取 ESP8266 传上来的 temp 和 hum 参数
    temp = request.args.get('temp')
    hum = request.args.get('hum')
    
    if temp is not None and hum is not None:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] 收到数据 -> 温度: {temp}°C, 湿度: {hum}%")
        
        # 将数据追加保存到本地 CSV 文件中
        try:
            with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([now_str, temp, hum])
            return "Data Saved Successfully", 200
        except Exception as e:
            print("写入 CSV 文件失败:", e)
            return "Internal Server Error", 500
    else:
        return "Bad Request: Missing parameters", 400

if __name__ == '__main__':
    # 监听 0.0.0.0 意味着局域网内的所有设备都可以通过你 PC 的局域网 IP 访问它
    # 使用端口 5000 
    app.run(host='0.0.0.0', port=5000, debug=True)