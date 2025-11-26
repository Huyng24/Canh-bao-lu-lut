# main_controller.py
import time
import json
import paho.mqtt.client as mqtt
from collections import deque
from datetime import datetime

# Import các module tự viết
import config
from modules import ai_dummy, radio_lora

class EdgeController:
    def __init__(self):
        # Biến trạng thái
        self.is_connected = False
        # Hàng đợi lưu trữ khi mất mạng (Lưu tối đa 2000 bản tin)
        self.offline_buffer = deque(maxlen=2000)
        
        # Cấu hình MQTT
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.is_connected = True
            print(f"✅ [MQTT] Đã kết nối Server {config.MQTT_BROKER}")
            # Gửi dữ liệu cũ ngay khi có mạng
            self.flush_buffer()
        else:
            print(f"❌ [MQTT] Kết nối thất bại mã: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.is_connected = False
        print("⚠️ [MQTT] Mất kết nối! Chuyển sang chế độ Offline.")

    def start(self):
        """Bắt đầu chạy hệ thống"""
        print("🚀 Hệ thống giám sát lũ lụt biên khởi động...")
        try:
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
            self.client.loop_start() # Chạy luồng ngầm MQTT
        except Exception as e:
            print(f"⚠️ Không thể kết nối Server ban đầu: {e}")

        # VÒNG LẶP CHÍNH (Main Loop)
        while True:
            try:
                self.process_cycle()
                time.sleep(2) # Chu kỳ lấy mẫu 2 giây
            except KeyboardInterrupt:
                print("Dừng hệ thống.")
                self.client.loop_stop()
                break

    def process_cycle(self):
        """Logic xử lý từng chu kỳ"""
        
        # 1. Lấy dữ liệu từ AI (Module của bạn kia)
        muc_nuoc, trang_thai = ai_dummy.get_ai_result()
        
        # 2. Tạo gói tin JSON chuẩn
        payload = {
            "device_id": "TRAM_01",
            "timestamp": datetime.now().isoformat(),
            "water_level": muc_nuoc,
            "status": trang_thai,
            "rtsp_link": config.RTSP_URL, # Gửi kèm link video
            "mode": "ONLINE" if self.is_connected else "OFFLINE_SAVED"
        }
        json_str = json.dumps(payload)

        # 3. Logic QUYẾT ĐỊNH (Decision Making)
        
        if self.is_connected:
            # --- TRƯỜNG HỢP CÓ MẠNG ---
            self.client.publish(config.MQTT_TOPIC_DATA, json_str)
            print(f"☁️ [Gửi Server] {muc_nuoc}cm - {trang_thai}")
            
        else:
            # --- TRƯỜNG HỢP MẤT MẠNG ---
            # A. Lưu vào bộ nhớ đệm
            self.offline_buffer.append(json_str)
            print(f"💾 [Lưu Buffer] {len(self.offline_buffer)} bản tin chờ gửi.")
            
            # B. Kiểm tra xem có cần báo động Radio không?
            # (Chỉ báo Radio khi mất mạng VÀ có nguy hiểm)
            if trang_thai in ["CANH_BAO", "NGUY_HIEM"]:
                radio_lora.send_emergency_signal(muc_nuoc, trang_thai)

    def flush_buffer(self):
        """Gửi bù dữ liệu khi có mạng lại"""
        if not self.offline_buffer:
            return

        print(f"🔄 Đang đồng bộ {len(self.offline_buffer)} bản tin cũ lên Server...")
        while self.offline_buffer:
            msg = self.offline_buffer.popleft()
            self.client.publish(config.MQTT_TOPIC_DATA, msg)
            time.sleep(0.05) # Delay nhỏ để tránh nghẽn mạng
        print("✅ Đồng bộ hoàn tất!")

# Chạy chương trình
if __name__ == "__main__":
    controller = EdgeController()
    controller.start()