import cv2
import time
import json
import os
import socket
import threading
import paho.mqtt.client as mqtt
from datetime import datetime
from ultralytics import YOLO # <--- THƯ VIỆN MỚI

# --- CẤU HÌNH ---
MQTT_BROKER = "192.168.1.X" # <--- THAY IP CỦA LAPTOP 2 VÀO ĐÂY
MQTT_PORT = 1883
MQTT_TOPIC = "flood/alert"
DEVICE_ID = "EDGE_UNIT_01"
MODEL_PATH = "CodeAI/flood_model.pt" # <--- TÊN FILE MODEL BẠN VỪA TẢI
CONF_THRESHOLD = 0.5          # Độ tin cậy (trên 50% mới báo)

# Giả lập GPIO
GPIO_PIN_SIREN = False 
client = None
is_connected = False

# --- SETUP AI MODEL ---
print("[INIT] Đang load model AI... Vui lòng chờ...")
model = YOLO(MODEL_PATH)
print("[INIT] Model loaded thành công!")

# --- CÁC HÀM MQTT & HARDWARE (GIỮ NGUYÊN NHƯ CŨ) ---
def setup_mqtt():
    global client, is_connected
    client = mqtt.Client()
    def on_connect(c, u, f, rc):
        global is_connected
        is_connected = (rc == 0)
    client.on_connect = on_connect
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except: pass

def send_alert_mqtt(message):
    if is_connected:
        client.publish(MQTT_TOPIC, json.dumps({"device_id": DEVICE_ID, "msg": message, "level": "DANGER"}))

def activate_physical_siren():
    global GPIO_PIN_SIREN
    if not GPIO_PIN_SIREN:
        GPIO_PIN_SIREN = True
        print("\n>>> [HARDWARE] CÒI HÚ VẬT LÝ KÍCH HOẠT! (OFF-GRID MODE) <<<\n")
        def turn_off():
            global GPIO_PIN_SIREN
            time.sleep(5)
            GPIO_PIN_SIREN = False
        threading.Thread(target=turn_off).start()

# --- MAIN PROCESS ---
def main():
    setup_mqtt()
    cap = cv2.VideoCapture(0) # 0 là Webcam, hoặc điền đường dẫn video file
    
    last_alert_time = 0
    
    # Kích thước khung hình hiển thị (giảm bớt để chạy nhanh hơn nếu cần)
    # cap.set(3, 640)
    # cap.set(4, 480)

    print("--- HỆ THỐNG GIÁM SÁT SẴN SÀNG ---")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # --- 1. AI INFERENCE (PHẦN QUAN TRỌNG NHẤT) ---
        # verbose=False để không in log rác ra terminal
        # stream=True giúp tối ưu bộ nhớ
        results = model(frame, conf=CONF_THRESHOLD, verbose=False, iou=0.5)
        
        flood_detected = False
        
        # Phân tích kết quả trả về
        for r in results:
            boxes = r.boxes
            if len(boxes) > 0: # Nếu phát hiện bất kỳ hộp nào -> CÓ LŨ
                flood_detected = True
                
                # Vẽ khung chữ nhật quanh vùng lũ
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Vẽ khung đỏ
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"FLOOD {float(box.conf):.2f}", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # --- 2. XỬ LÝ LOGIC CẢNH BÁO ---
        current_time = time.time()
        
        if flood_detected:
            # Hiển thị cảnh báo trên màn hình
            cv2.putText(frame, "!!! NGUY HIEM: NUOC DANG !!!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            # Cơ chế Debounce: Chỉ gửi cảnh báo mỗi 5 giây/lần
            if current_time - last_alert_time > 5:
                # Gửi về Server (nếu có mạng)
                send_alert_mqtt("Phát hiện nước lũ dâng cao!")
                
                # Kích hoạt còi hú (luôn chạy kể cả mất mạng)
                activate_physical_siren()
                
                last_alert_time = current_time

        else:
            # Trạng thái an toàn
            cv2.putText(frame, "Trang thai: Binh thuong", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # --- 3. HIỂN THỊ ---
        # Hiển thị trạng thái kết nối mạng
        net_stt = "NET: ONLINE" if is_connected else "NET: OFFLINE"
        cv2.putText(frame, net_stt, (10, frame.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        
        cv2.imshow("Edge AI Monitor", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()