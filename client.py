import dht
import machine
import network
import time
import urequests
import gc
from machine import Pin

# === 提升主频至 160MHz，增强 WiFi 开启时微秒级采样的抗干扰能力 ===
machine.freq(160000000)

# ====================== 用户配置区 ======================
WIFI_SSID = "ESP"
WIFI_PWD  = "esp11111"

# 你的云端或局域网接收地址（请根据实际需要修改）
TARGET_URLS = [
    "http://你的阿里云公网IP:端口/路径",
    "http://你的PC局域网IP:端口/your_endpoint"
]

DHT_PIN = 4                # GPIO4 (对应开发板丝印 D2)
LED_PIN = 2                # 板载LED (对应开发板丝印 D4)
NORMAL_INTERVAL = 60       # 常规数据上报周期(单位：秒)
# =======================================================

# 传感器初始化：开启内部上拉，确保信号稳定
dht_io = Pin(DHT_PIN, Pin.IN, Pin.PULL_UP)
dht_sensor = dht.DHT22(dht_io)

# 板载LED初始化：默认熄灭 (NodeMCU 板载 LED 为低电平点亮，1为灭)
led = Pin(LED_PIN, Pin.OUT, value=1) 

def connect_wifi(retries=15):
    """连接 WiFi（带重试机制）"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(WIFI_SSID, WIFI_PWD)
        for _ in range(retries):
            if wlan.isconnected():
                break
            time.sleep(1)
            
    if wlan.isconnected():
        print("WiFi connected! IP:", wlan.ifconfig()[0])
        # 连上 WiFi 后闪烁一次 LED 确认
        led.value(0)
        time.sleep(0.5)
        led.value(1)
        return wlan
    else:
        print("WiFi failed, restarting...")
        machine.reset()

def read_sensor(max_tries=3):
    """读取温湿度数据（带 >= 2s 冷却时间的自动重试机制）"""
    for i in range(max_tries):
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
            print("Sensor Data: temp={:.1f}°C  hum={:.1f}%".format(temp, hum))
            return temp, hum
        except Exception as e:
            print("Sensor error (try {}/{}): {}".format(i+1, max_tries, e))
            # 必须等待大于 2 秒，DHT22 硬件状态机才能复位响应下一次尝试
            time.sleep(2.5)
    return None, None

def report_to_url(url, temp, hum):
    """向指定 URL 发送 HTTP GET 请求"""
    try:
        payload = "?temp={:.1f}&hum={:.1f}".format(temp, hum)
        full_url = url + payload
        print("Sending to:", full_url)
        
        r = urequests.get(full_url)
        _ = r.text  # 必须读取一次响应内容以清空接收缓冲区，防止内存泄漏
        r.close()   # 必须显式关闭 socket 连接以释放资源
        
        print(" -> Success")
        return True
    except Exception as e:
        print(" -> Failed:", e)
        return False

def report_to_all(temp, hum):
    """向所有配置的目标服务器上报数据"""
    for url in TARGET_URLS:
        report_to_url(url, temp, hum)
        time.sleep_ms(200) # 网络请求之间给予芯片短暂喘息时间
    gc.collect()           # 网络请求容易产生大量零碎内存，强制进行一次垃圾回收

def main():
    # 1. 启动时连接 WiFi
    connect_wifi()
    
    # 2. 周期上报循环
    while True:
        cycle_start = time.time()
        
        # 第一步：读取传感器
        temp, hum = read_sensor()
        
        # 第二步：读取成功则点亮 LED 并上报
        if temp is not None:
            led.value(0) # 上报期间点亮蓝灯
            report_to_all(temp, hum)
            led.value(1) # 上报结束熄灭蓝灯
        else:
            print("Skipping report due to sensor failure.")
            
        # 第三步：周期垃圾回收，优化可用内存空间
        gc.collect()
        
        # 第四步：计算实际执行耗时，休眠至下一个周期
        elapsed = time.time() - cycle_start
        sleep_time = NORMAL_INTERVAL - elapsed
        if sleep_time < 0:
            sleep_time = 0
            
        print("Waiting {} seconds for next cycle...\n".format(int(sleep_time)))
        time.sleep(sleep_time)

if __name__ == "__main__":
    time.sleep(1.5) # 极重要：开机延迟，给电容充饱电，让硬件电压平稳后才开始读取
    main()