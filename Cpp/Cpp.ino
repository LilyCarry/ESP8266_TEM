#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>

// ==================== 硬件引脚定义 ====================
#define DHTPIN 14         // DHT22 数据脚接 GPIO14 (对应 D5 引脚)
#define DHTTYPE DHT22     
#define LED_PIN 2         // 板载蓝灯接 GPIO2 (D4 引脚)

DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);

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

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  
  dht.begin();      // 初始化温湿度
  
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

    // 发送数据到华为云
    char payload[256];
    snprintf(payload, sizeof(payload), 
             "{\"services\": [{\"service_id\": \"dht22\", \"properties\": {\"temp\": %.1f, \"hum\": %.1f}}]}", 
             temp, hum);

    digitalWrite(LED_PIN, LOW);
    if (client.publish(mqtt_topic, payload)) {
      Serial.println(" -> Cloud Publish Success!");
    }
    digitalWrite(LED_PIN, HIGH);
  }
}