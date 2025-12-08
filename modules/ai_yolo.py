# modules/ai_yolo.py
from ultralytics import YOLO
import cv2
import config

class FloodDetector:
    def __init__(self):
        print(f"🧠 [AI] Đang tải model: {config.AI_MODEL_PATH}...")
        try:
            self.model = YOLO(config.AI_MODEL_PATH)
            # In ra danh sách các Class mà model này học được để kiểm tra
            print(f"✅ [AI] Model đã tải thành công!")
            print(f"📋 Danh sách Class model nhận diện: {self.model.names}")
        except Exception as e:
            print(f"❌ [AI] Lỗi tải Model (File lỗi hoặc sai đường dẫn): {e}")
            self.model = None

    def detect(self, frame):
        """
        Input: Khung hình Camera
        Output: Mực nước (ước lượng), Trạng thái, Khung hình đã vẽ báo động
        """
        if self.model is None or frame is None:
            return 0, "LOI_MODEL", frame

        # Chạy nhận diện
        results = self.model(frame, conf=config.AI_CONF_THRESHOLD, verbose=False)
        
        is_flood = False
        water_level = 50.0 # Mức nước bình thường (giả định)
        
        # --- LOGIC XỬ LÝ MODEL CUSTOM ---
        for r in results:
            boxes = r.boxes
            
            # Nếu model phát hiện ra bất cứ cái gì -> Coi là có dấu hiệu nước/lũ
            if len(boxes) > 0:
                is_flood = True
                
                for box in boxes:
                    # Lấy thông tin hộp
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    conf = float(box.conf)
                    cls_id = int(box.cls[0])
                    class_name = self.model.names[cls_id] # Tên class (vd: 'flood')

                    # Tính toán mức nước giả định dựa trên độ cao của hộp phát hiện
                    # Hộp càng to/càng cao -> Nước càng dâng
                    height_img = frame.shape[0]
                    bbox_height = y2 - y1
                    # Công thức ước lượng: Vật thể chiếm bao nhiêu % khung hình
                    water_level = 100 + (bbox_height / height_img) * 200 

                    # Vẽ khung cảnh báo
                    color = (0, 0, 255) # Màu đỏ
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Viết tên class và độ tin cậy
                    label = f"{class_name} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Quyết định trạng thái cuối cùng
        if is_flood:
            status = "NGUY_HIEM"
            cv2.putText(frame, f"CANH BAO: {status}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        else:
            status = "AN_TOAN"
            water_level = 80.0 # Mức thấp
            cv2.putText(frame, "BINH THUONG", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return water_level, status, frame