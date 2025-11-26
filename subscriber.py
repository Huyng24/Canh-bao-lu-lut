import paho.mqtt.client as mqtt
import json
import time

# Cấu hình
BROKER = "localhost" 
TOPIC = "lu_lut/tram_01/data"

# --- HÀM XỬ LÝ KHI KẾT NỐI THÀNH CÔNG ---
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ Đã kết nối lại với Broker!")
        # QUAN TRỌNG: Đăng ký topic NGAY TẠI ĐÂY
        # Để khi mất mạng có lại, nó tự động đăng ký lại
        client.subscribe(TOPIC)
        print(f"📡 Đã đăng ký lắng nghe: {TOPIC}")
    else:
        print(f"Lỗi kết nối: {reason_code}")

# --- HÀM XỬ LÝ KHI MẤT KẾT NỐI ---
def on_disconnect(client, userdata, flags, reason_code, properties):
    print("⚠️ Mất kết nối tới Broker. Đang thử kết nối lại...")

# --- HÀM NHẬN TIN NHẮN ---
def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        
        device = data.get("device_id")
        level = data.get("water_level")
        status = data.get("status")
        mode = data.get("mode", "UNKNOWN")
        timestamp = data.get("timestamp")

        # Đánh dấu tin nhắn gửi bù
        prefix = "☁️ [LIVE]"
        if mode == "OFFLINE_SAVED":
            prefix = "💾 [HISTORY]"

        print(f"{prefix} {timestamp} | Trạm: {device} | Nước: {level}cm | Trạng thái: {status}")
        
        if status in ["CANH_BAO", "NGUY_HIEM"]:
             print(f"   >>> 🚨 CẢNH BÁO: {status} <<<")

    except Exception as e:
        print(f"Lỗi đọc tin nhắn: {e}")

# --- CHẠY CHƯƠNG TRÌNH ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Gán các hàm callback
client.on_connect = on_connect       # <--- Gán hàm xử lý kết nối
client.on_disconnect = on_disconnect # <--- Gán hàm xử lý ngắt
client.on_message = on_message

print(f"📡 SERVER ĐANG KHỞI ĐỘNG (Broker: {BROKER})...")

while True:
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_forever() # Tự động reconnect nếu rớt mạng
    except Exception as e:
        print(f"Không tìm thấy Broker. Thử lại sau 3s... ({e})")
        time.sleep(3)