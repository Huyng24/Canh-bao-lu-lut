# cấu hình AI phân tích
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
            print(f"✅ [AI] Model đã tải thành công! (Chế độ: SAFETY LINE)")
        except Exception as e:
            print(f"❌ [AI] Lỗi tải Model: {e}")
            self.model = None

        # --- CẤU HÌNH  ---
        # Trong OpenCV, trục Y tăng từ trên xuống dưới.
        # Giá trị càng nhỏ thì càng ở cao.
        self.SAFETY_LINE_Y = 350  # Ngưỡng cảnh báo 

        # Màu sắc 
        self.COLOR_SAFE = (0, 255, 0)   # Xanh lá
        self.COLOR_WARN = (0, 0, 255)   # Đỏ
        self.COLOR_BOX  = (0, 255, 255) # Vàng (Khung nước)

    def detect(self, frame):
        """
        Input: Frame hình ảnh
        Output: Mực nước (ước lượng), Trạng thái, Frame đã vẽ
        """
        if self.model is None or frame is None:
            return 0, "LOI_MODEL", frame

        height, width = frame.shape[:2]
        
        # 1. AI Inference 
        results = self.model(frame, conf=config.AI_CONF_THRESHOLD, verbose=False, iou=0.5)
        
        water_detected = False
        highest_water_y = height 
        
        # 2. Phân tích kết quả
        for r in results:
            boxes = r.boxes
            if len(boxes) > 0:
                water_detected = True
                
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Cập nhật điểm cao nhất của nước (y1 càng nhỏ là càng cao)
                    if y1 < highest_water_y:
                        highest_water_y = y1
                    
                    # Vẽ khung nước 
                    cv2.rectangle(frame, (x1, y1), (x2, y2), self.COLOR_BOX, 2)
                    cv2.putText(frame, "WATER", (x1, y1 - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.COLOR_BOX, 1)

        # 3. XỬ LÝ LOGIC ĐƯỜNG THAM CHIẾU
        is_flooding = False
        status = "AN_TOAN"
        
        # Logic: Nếu có nước và đỉnh nước cao hơn (nhỏ hơn) đường an toàn
        if water_detected and highest_water_y < self.SAFETY_LINE_Y:
            is_flooding = True
            status = "NGUY_HIEM"

        # 4. VẼ GIAO DIỆN & CẢNH BÁO
        if is_flooding:
            # --- TRẠNG THÁI: NGUY HIỂM ---
            # Vẽ đường tham chiếu màu đỏ
            cv2.line(frame, (0, self.SAFETY_LINE_Y), (width, self.SAFETY_LINE_Y), self.COLOR_WARN, 3)
            cv2.putText(frame, f"CANH BAO (Y={self.SAFETY_LINE_Y})", (10, self.SAFETY_LINE_Y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WARN, 2)
            
            # Hiển thị chữ cảnh báo 
            cv2.putText(frame, "!!! NUOC VUOT MUC !!!", (50, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, self.COLOR_WARN, 3)
        else:
            # --- TRẠNG THÁI: AN TOÀN ---
            # Vẽ đường tham chiếu màu xanh
            cv2.line(frame, (0, self.SAFETY_LINE_Y), (width, self.SAFETY_LINE_Y), self.COLOR_SAFE, 2)
            cv2.putText(frame, f"AN TOAN (Y={self.SAFETY_LINE_Y})", (10, self.SAFETY_LINE_Y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_SAFE, 2)
            
            # Hiển thị chữ trạng thái
            if water_detected:
                cv2.putText(frame, "Phat hien nuoc (An toan)", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, self.COLOR_SAFE, 2)

        # --- TÍNH TOÁN CON SỐ MỰC NƯỚC (Để gửi lên Dashboard) ---
        # Vì Dashboard cần một con số để vẽ biểu đồ, ta quy đổi ngược:
        # Mực nước = Chiều cao ảnh - Vị trí Y của nước (nước càng cao thì số càng lớn)
        if water_detected:
            pixels_from_bottom = height - highest_water_y
            calculated_level = pixels_from_bottom * 1.5
        else:
            calculated_level = 0

        # Hiển thị số đo góc trái dưới 
        cv2.putText(frame, f"Level: {calculated_level} (Y:{highest_water_y})", (10, height - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return calculated_level, status, frame
#