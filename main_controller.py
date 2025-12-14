# main_controller.py
import time
import json
import cv2
import paho.mqtt.client as mqtt
from collections import deque
from datetime import datetime
import base64

# thử ÉP OPENCV DÙNG TCP (Ổn định hơn UDP)
import os # <--- Nhớ import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

# Import module cấu hình và các module chức năng
import config
from modules import radio_lora, ai_yolo  # <--- Đã đổi sang dùng AI YOLO thật

class EdgeController:
    def __init__(self):
        # Biến trạng thái kết nối
        self.is_connected = False
        # Hàng đợi lưu trữ khi mất mạng (Lưu tối đa 2000 bản tin)
        self.offline_buffer = deque(maxlen=2000)
        
        # 1. Khởi tạo MQTT Client
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        
        # 2. Khởi tạo AI Engine (Load Model YOLO)
        # Bước này sẽ tốn chút thời gian để load file .pt
        self.ai_engine = ai_yolo.FloodDetector()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.is_connected = True
            print(f"✅ [MQTT] Đã kết nối Server {config.MQTT_BROKER}")
            # Gửi bù dữ liệu cũ ngay khi có mạng lại
            self.flush_buffer()
        else:
            print(f"❌ [MQTT] Kết nối thất bại mã: {reason_code}")

    def on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.is_connected = False
        print("⚠️ [MQTT] Mất kết nối! Chuyển sang chế độ Offline.")

    def start(self):
        print("🚀 Hệ thống EDGE AI khởi động...")
        
        # --- BƯỚC 1: KẾT NỐI MQTT ---
        try:
            self.client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
            self.client.loop_start() # Chạy luồng ngầm để giữ kết nối
        except Exception as e:
            print(f"⚠️ Lỗi MQTT ban đầu (Hệ thống vẫn chạy Offline): {e}")

        # --- BƯỚC 2: KẾT NỐI CAMERA (RTSP) ---
        print(f"🎥 Đang kết nối luồng Video: {config.RTSP_URL}")
        cap = cv2.VideoCapture(config.RTSP_URL)

        if not cap.isOpened():
            print("❌ LỖI NGHIÊM TRỌNG: Không thể mở luồng Video!")
            print("   -> Hãy kiểm tra lại: FFmpeg đã chạy chưa? IP ZeroTier đúng chưa?")
            return

        # --- BƯỚC 3: VÒNG LẶP CHÍNH (XỬ LÝ LIÊN TỤC) ---
        while True:
            try:
                # 1. Đọc khung hình từ luồng Video
                ret, frame = cap.read()
                if not ret:
                    print("⚠️ Mất tín hiệu Video! Đang thử kết nối lại sau 2 giây...")
                    cap.release() # Hủy kết nối cũ
                    time.sleep(2) 
                    # Thử kết nối lại
                    cap = cv2.VideoCapture(config.RTSP_URL)
                    if not cap.isOpened():
                        print("❌ Vẫn chưa kết nối được...")
                    else:
                        print("✅ Đã kết nối lại thành công!")
                    continue

                # 2. Đưa ảnh cho AI xử lý
                # Hàm này trả về: Mực nước, Trạng thái, và Ảnh đã vẽ khung
                muc_nuoc, trang_thai, processed_frame = self.ai_engine.detect(frame)

                # --- [QUAN TRỌNG] KÍCH HOẠT CẢNH BÁO TẠI CHỖ ---
                # Nếu Nguy Hiểm -> Gọi Module Radio (đã tích hợp còi hú)
                # Gọi bất kể có mạng hay không (Ưu tiên an toàn số 1)
                if trang_thai == "NGUY_HIEM":
                    radio_lora.send_emergency_signal(muc_nuoc, trang_thai)
                # -----------------------------------------------

                # (Tùy chọn) Hiện cửa sổ xem trước trên máy Edge để debug
                # Bạn có thể bỏ comment dòng dưới nếu muốn xem trực tiếp trên máy này
                cv2.imshow("Edge Monitor", processed_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'): break

                # 3. Tạo gói tin JSON
                payload = {
                    "device_id": "TRAM_01",
                    "timestamp": datetime.now().isoformat(),
                    "water_level": muc_nuoc,
                    "status": trang_thai,
                    "rtsp_link": config.RTSP_URL, # Gửi kèm link để Web biết đường mở video
                    "mode": "ONLINE" if self.is_connected else "OFFLINE_SAVED"
                }
                json_str = json.dumps(payload)

                # 4. Logic Quyết định (Gửi đi hay Lưu lại?)
                if self.is_connected:
                    # A. CÓ MẠNG: Gửi ngay 
                    self.client.publish(config.MQTT_TOPIC_DATA, json_str)
                    # Phần mở rộng tùy chọn: gửi ảnh AI đã phân tích lên web
                    # Resize ảnh nhỏ lại (480x360) cho nhẹ mạng, Web load nhanh
                    small_frame = cv2.resize(processed_frame, (480, 360))
                    # Nén sang JPG chất lượng 60%
                    _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    # Chuyển sang Base64 để gửi qua MQTT
                    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
                    # Gửi vào topic hình ảnh
                    self.client.publish(config.MQTT_TOPIC_IMAGE, jpg_as_text)
                    #---
                    print(f"☁️ [Online] Nước: {muc_nuoc:.1f}cm | {trang_thai}")
                else:
                    # C. MẤT MẠNG: Lưu vào Buffer
                    self.offline_buffer.append(json_str)
                    print(f"💾 [Offline] Đã lưu {len(self.offline_buffer)} tin.")
                    

                # Giảm tải CPU (AI chạy nặng, sleep ít thôi)
                # Chỉnh số này nếu muốn gửi nhanh hơn hoặc chậm hơn
                time.sleep(0.5) 

            except KeyboardInterrupt:
                print("\n🛑 Dừng hệ thống theo yêu cầu người dùng.")
                self.client.loop_stop()
                cap.release()
                cv2.destroyAllWindows()
                break
            except Exception as e:
                print(f"❌ Lỗi trong vòng lặp chính: {e}")
                time.sleep(1)

    def flush_buffer(self):
        """Gửi bù dữ liệu từ bộ nhớ đệm khi có mạng lại"""
        if not self.offline_buffer: return
        
        count = len(self.offline_buffer)
        print(f"🔄 Đang đồng bộ {count} bản tin cũ lên Server...")
        
        while self.offline_buffer:
            msg = self.offline_buffer.popleft()
            self.client.publish(config.MQTT_TOPIC_DATA, msg)
            time.sleep(0.01) # Delay nhỏ để tránh nghẽn mạng MQTT
            
        print("✅ Đồng bộ hoàn tất!")

# Chạy chương trình
if __name__ == "__main__":
    controller = EdgeController()
    controller.start()
#