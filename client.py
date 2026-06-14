import dht
import machine
import network
import socket
import time
import urequests
import ujson
from machine import Pin

# ====================== 用户配置区 ======================
WIFI_SSID = "Carry"
WIFI_PWD  = "carry123"

TARGET_URLS = [
    "http://你的阿里云公网IP:端口/路径",
    "http://你的PC局域网IP:端口/your_endpoint"
]

DHT_PIN = 4                # GPIO4 (D2)
LED_PIN = 2                # 板载LED (GPIO2, D4)
TCP_PORT = 12345
NORMAL_INTERVAL = 60
REAL_TIME_INTERVAL = 1
# =======================================================

dht_sensor = dht.DHT22(Pin(DHT_PIN))
led = Pin(LED_PIN, Pin.OUT)
led.value(1)

# WiFi 连接（带重试）
def connect_wifi(retries=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.disconnect()
    for i in range(retries):
        if wlan.isconnected():
            break
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PWD)
        for _ in range(20):  # 等待约10秒
            if wlan.isconnected():
                break
            time.sleep(0.5)
    if wlan.isconnected():
        print("WiFi connected, IP:", wlan.ifconfig()[0])
        led.value(1)
        return wlan
    else:
        print("WiFi failed, restarting...")
        machine.reset()

# 读取温湿度（带重试）
def read_sensor(max_tries=3):
    for _ in range(max_tries):
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
            print("Sensor: temp={:.1f}°C  hum={:.1f}%".format(temp, hum))
            return temp, hum
        except Exception as e:
            print("Sensor error:", e)
            time.sleep(0.5)
    return None, None

def report_to_url(url, temp, hum):
    try:
        payload = "?temp={:.1f}&hum={:.1f}".format(temp, hum)
        full_url = url + payload
        r = urequests.get(full_url, timeout=3)
        r.close()
        print("Report success:", url)
        return True
    except Exception as e:
        print("Report failed to", url, "error:", e)
        return False

def report_to_all(temp, hum):
    for url in TARGET_URLS:
        report_to_url(url, temp, hum)
        time.sleep_ms(100)

# 处理实时客户端（非阻塞发送）
def handle_realtime_client(client):
    addr = client.getpeername()
    print("Real-time client connected from", addr)
    led.value(0)
    client.setblocking(False)
    last_send = 0
    # 持续服务，直到客户端断开或出错
    while True:
        now = time.time()
        if now - last_send >= REAL_TIME_INTERVAL:
            temp, hum = read_sensor()
            if temp is not None:
                data = ujson.dumps({"temp": temp, "hum": hum, "ts": now}) + "\n"
                try:
                    client.send(data)
                    last_send = now
                except OSError as e:
                    if e.args[0] == 11:  # EAGAIN, 缓冲区满，稍后重试
                        pass
                    else:
                        print("Send error:", e)
                        break
            else:
                # 传感器错误也稍微等待
                time.sleep(1)
                continue
        # 尝试接收数据以检测客户端断开
        try:
            if client.recv(1024) == b'':
                break
        except OSError as e:
            if e.args[0] == 11:  # 无数据可用，正常
                pass
            else:
                print("Recv error:", e)
                break
        time.sleep_ms(100)
    client.close()
    led.value(1)
    print("Real-time client disconnected")

def main():
    wlan = connect_wifi()
    
    # 创建非阻塞 TCP 服务器
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', TCP_PORT))
    server.listen(1)
    server.setblocking(False)   # 非阻塞模式
    print("TCP server listening on port", TCP_PORT)
    
    last_report = 0
    # 主循环
    while True:
        now = time.time()
        
        # 1. 定时上报
        if now - last_report >= NORMAL_INTERVAL:
            temp, hum = read_sensor()
            if temp is not None:
                report_to_all(temp, hum)
            else:
                # 传感器失败时也稍作延时，避免疯狂重试
                time.sleep(2)
            last_report = now
        
        # 2. 检查新客户端连接（非阻塞）
        try:
            client, addr = server.accept()
            # 有客户端连接，进入实时模式（阻塞直到断开）
            handle_realtime_client(client)
        except OSError as e:
            if e.args[0] == 11:  # EAGAIN，无连接
                pass
            else:
                print("Accept error:", e)
        
        time.sleep_ms(200)

if __name__ == "__main__":
    main()