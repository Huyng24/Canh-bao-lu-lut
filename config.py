# Cài đặt cấu hình

# Cấu hình MQTT Broker 
MQTT_BROKER = "10.147.20.109"
MQTT_PORT = 1883
MQTT_TOPIC_DATA = "lu_lut/tram_01/data"
MQTT_TOPIC_STATUS = "lu_lut/tram_01/status"
# Tùy chọn mở rộng: gửi video AI đã xử lý lên web
MQTT_TOPIC_IMAGE = "lu_lut/tram_01/image"

# Cấu hình Camera RTSP 
RTSP_URL = "rtsp://10.147.20.109:8554/live" 

# Ngưỡng cảnh báo (cm)
LEVEL_ALARM_1 = 150 # Báo động cấp 1
LEVEL_ALARM_2 = 200 # Báo động cấp 2 (Nguy hiểm)

# Cấu hình Radio (LoRa)
LORA_FREQ = 433.0

# --- CẤU HÌNH AI ---
AI_MODEL_PATH = "flood_model.pt" 
AI_CONF_THRESHOLD = 0.5 # Độ tin cậy (trên 50% mới báo)
#