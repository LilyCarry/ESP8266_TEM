#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <ir_Mitsubishi.h> // 引入三菱空调协议库

// ==================== 硬件引脚定义 ====================
#define DHTPIN 4          // DHT22 数据脚接 GPIO4 (D2 引脚)
#define DHTTYPE DHT22     
#define LED_PIN 2         // 板载蓝灯接 GPIO2 (D4 引脚)
const uint16_t kIrLed = 5;  // 红外发射管接 GPIO5 (D1 引脚)

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);
IRMitsubishiAC ac(kIrLed);  // 创建三菱空调控制对象

// ====================== 用户配置区 ======================
const char* ssid     = "ESP";         
const char* password = "esp11111";    

const char* mqtt_server   = "8820a9b6da.st1.iotda-device.cn-east-3.myhuaweicloud.com";
const int mqtt_port       = 1883;
const char* mqtt_clientId = "6a2e999ce094d6159247eb5f_ESP8266_DHT22_0_0_2026061813";
const char* mqtt_username = "6a2e999ce094d6159247eb5f_ESP8266_DHT22";
const char* mqtt_password = "b8051fcaafbc2611df1339d9b6f7860c6c5edebf0859b0d4d5e026fc4ba2aefa";

const char* mqtt_topic    = "$oc/devices/6a2e999ce094d6159247eb5f_ESP8266_DHT22/sys/properties/report";

unsigned long last_msg_time = 0;
const long interval = 15000; // 每 15 秒上报一次
// ========================================================

void connect_wifi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection to Huawei Cloud...");
    if (client.connect(mqtt_clientId, mqtt_username, mqtt_password)) {
      Serial.println("connected!");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

// ⭐ 核心逻辑：空调自动控制函数
void control_ac_by_temp(float temp) {
  if (temp >= 18.0) {
    Serial.println("[IR CONTROL] Temp >= 28C. Turning ON Mitsubishi AC (Cool, 26C)...");
    ac.on();                             // 开启空调
    ac.setFan(kMitsubishiAcFanAuto);       // 设置风速自动
    ac.setMode(kMitsubishiAcCool);         // 设置制冷模式
    ac.setTemp(26);                      // 设置目标温度 26 度
    ac.send();                           // 发送红外信号！
  } 
  else if (temp <= 10.0) {
    Serial.println("[IR CONTROL] Temp <= 24C. Turning OFF Mitsubishi AC...");
    ac.off();                            // 关闭空调
    ac.send();                           // 发送红外信号！
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  
  dht.begin();      // 初始化温湿度
  ac.begin();       // 初始化红外发射

  // 默认先把空调状态设置为关机，防止乱发信号
  ac.off(); 
  
  connect_wifi();
  client.setServer(mqtt_server, mqtt_port);
  
  client.setBufferSize(512);   
  client.setKeepAlive(60);     
}

void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  unsigned long now = millis();
  if (now - last_msg_time > interval) {
    last_msg_time = now;

    float temp = dht.readTemperature();
    float hum = dht.readHumidity();

    if (isnan(temp) || isnan(hum)) {
      Serial.println("Failed to read DHT!");
      return;
    }

    Serial.printf("Sensor Data: Temp: %.1fC, Hum: %.1f%%\n", temp, hum);

    // 1. 发送数据到华为云
    char payload[256];
    snprintf(payload, sizeof(payload), 
             "{\"services\": [{\"service_id\": \"dht22\", \"properties\": {\"temp\": %.1f, \"hum\": %.1f}}]}", 
             temp, hum);

    digitalWrite(LED_PIN, LOW);
    if (client.publish(mqtt_topic, payload)) {
      Serial.println(" -> Cloud Publish Success!");
    }
    digitalWrite(LED_PIN, HIGH);

    // 2. 根据温度控制空调
    control_ac_by_temp(temp);
  }
}