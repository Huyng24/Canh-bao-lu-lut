# modules/ai_yolo.py
import cv2
import numpy as np
from ultralytics import YOLO
import config

class FloodDetector:
    def __init__(self):
        print(f"🧠 [AI] Đang tải model: {config.AI_MODEL_PATH}...")
        try:
            self.model = YOLO(config.AI_MODEL_PATH)
            print(f"✅ [AI] Model đã tải thành công!")
        except Exception as e:
            print(f"❌ [AI] Lỗi tải Model: {e}")
            self.model = None

        # --- CẤU HÌNH VÙNG CẢNH BÁO (ROI) ---
        # Định nghĩa 4 điểm tạo thành hình tứ giác (vùng sông/suối)
        # Bạn cần chỉnh các số này cho khớp với góc quay camera thực tế
        # Tọa độ: [x, y]
        self.zone_polygon = np.array([
            [100, 480],   # Điểm dưới cùng bên trái
            [200, 200],   # Điểm trên cùng bên trái (xa xa)
            [440, 200],   # Điểm trên cùng bên phải (xa xa)
            [540, 480]    # Điểm dưới cùng bên phải
        ], np.int32)
        
        # Màu sắc
        self.COLOR_ZONE = (255, 255, 0) # Màu xanh lơ (Vùng an toàn)
        self.COLOR_WARN = (0, 0, 255)   # Màu đỏ (Khi có lũ)

    def detect(self, frame):
        """
        Input: Frame hình ảnh
        Output: Mực nước (cm), Trạng thái, Frame đã vẽ
        """
        if self.model is None or frame is None:
            return 0, "LOI_MODEL", frame

        # 1. Vẽ vùng cảnh báo lên màn hình để dễ quan sát
        # reshape để đúng định dạng opencv
        cv2.polylines(frame, [self.zone_polygon], isClosed=True, color=self.COLOR_ZONE, thickness=2)

        # 2. Chạy nhận diện AI
        results = self.model(frame, conf=config.AI_CONF_THRESHOLD, verbose=False)
        
        max_water_level = 0.0
        is_flood_in_zone = False
        
        height_img, width_img = frame.shape[:2]

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Lấy tọa độ hộp
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Tính điểm trung tâm đáy của hộp (chân của dòng nước/vật thể)
                # Đây là điểm quan trọng nhất để tính mực nước
                cx = int((x1 + x2) / 2)
                cy = int(y2) 

                # 3. Kiểm tra xem điểm này có nằm trong vùng cảnh báo không?
                # measureDist=False: chỉ cần trả về +1 (trong), -1 (ngoài), 0 (trên cạnh)
                is_inside = cv2.pointPolygonTest(self.zone_polygon, (cx, cy), False)

                if is_inside >= 0:
                    is_flood_in_zone = True
                    
                    # --- TÍNH TOÁN MỰC NƯỚC (Logic mới) ---
                    # Giả định: Đáy ảnh (y=480) là 0cm, Đỉnh vùng (y=200) là 200cm
                    # Dùng hàm nội suy tuyến tính để map tọa độ Y sang Cm
                    # pixel_y càng nhỏ (càng lên cao) -> mực nước càng cao
                    
                    y_min_zone = 200 # Tương ứng điểm cao nhất của vùng
                    y_max_zone = 480 # Tương ứng điểm thấp nhất của vùng
                    
                    # Công thức map: Y thực tế -> [0cm - 200cm]
                    current_level = np.interp(cy, [y_min_zone, y_max_zone], [200, 0])
                    
                    if current_level > max_water_level:
                        max_water_level = round(current_level, 1)

                    # Vẽ cảnh báo đỏ rực
                    cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_WARN, 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1) # Chấm điểm tâm
                    cv2.putText(frame, f"Water: {max_water_level}cm", (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WARN, 2)
                else:
                    # Nếu vật thể ở ngoài vùng, vẽ màu xám cho biết "tao thấy mày nhưng tao kệ"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 1)

        # 4. Xác định trạng thái cuối cùng
        status = "AN_TOAN"
        if is_flood_in_zone:
            if max_water_level >= config.LEVEL_ALARM_2:
                status = "NGUY_HIEM"
            elif max_water_level >= config.LEVEL_ALARM_1:
                status = "CANH_BAO"
            
            # Đổi màu khung vùng thành màu đỏ để báo động tổng thể
            cv2.polylines(frame, [self.zone_polygon], isClosed=True, color=self.COLOR_WARN, thickness=3)
            
        # Hiển thị thông tin lên góc màn hình
        cv2.putText(frame, f"LEVEL: {max_water_level}cm | {status}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        return max_water_level, status, frame