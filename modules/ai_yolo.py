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

        # --- CẤU HÌNH THƯỚC ĐO ---
        self.ALARM_LINE_Y = 250         # Vị trí dòng kẻ báo động (pixel)
        self.MAX_REAL_LEVEL_CM = 500.0  # Giả sử đỉnh màn hình (y=0) là 500cm
        self.MIN_REAL_LEVEL_CM = 0.0    # Đáy màn hình (y=max) là 0cm
        
        # Màu sắc giao diện
        self.COLOR_SAFE = (0, 255, 0)   # Xanh lá
        self.COLOR_WARN = (0, 0, 255)   # Đỏ
        self.COLOR_RULER = (255, 255, 0)# Vàng

    def calculate_water_level(self, y_pixel, height_img):
        """
        Hàm chuyển đổi từ tọa độ Pixel (Y) sang Centimet (CM)
        Công thức: Nội suy tuyến tính (Linear Interpolation)
        """
        # Ngăn chia cho 0
        if height_img == 0: return 0.0
        
        # Công thức map: 
        # y = height (đáy) -> 0 cm
        # y = 0 (đỉnh)     -> 500 cm
        
        # np.interp(giá_trị_cần_tính, [input_min, input_max], [output_min, output_max])
        level_cm = np.interp(y_pixel, [0, height_img], [self.MAX_REAL_LEVEL_CM, self.MIN_REAL_LEVEL_CM])
        
        # Làm tròn 1 số thập phân và không để số âm
        return max(0.0, round(level_cm, 1))

    def draw_virtual_ruler(self, frame):
        """
        Vẽ thước đo ảo bên trái màn hình để trực quan hóa độ cao
        """
        h, w = frame.shape[:2]
        # Vẽ trục dọc
        cv2.line(frame, (20, 0), (20, h), self.COLOR_RULER, 2)
        
        # Vẽ các vạch chia (Mỗi 100cm vẽ 1 vạch)
        step_cm = 100
        for cm in range(0, int(self.MAX_REAL_LEVEL_CM) + 1, step_cm):
            # Tính ngược từ CM ra Pixel Y để vẽ vạch
            y_pos = int(np.interp(cm, [self.MIN_REAL_LEVEL_CM, self.MAX_REAL_LEVEL_CM], [h, 0]))
            
            # Vẽ vạch ngang nhỏ
            cv2.line(frame, (20, y_pos), (35, y_pos), self.COLOR_RULER, 2)
            # Viết số CM
            cv2.putText(frame, f"{cm}", (40, y_pos + 5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.COLOR_RULER, 1)

    def detect(self, frame):
        if self.model is None or frame is None:
            return 0, "LOI_MODEL", frame

        height_img, width_img = frame.shape[:2]
        
        # 1. Vẽ thước đo ảo (Tính năng mới)
        self.draw_virtual_ruler(frame)
        
        # 2. Vẽ đường Line cảnh báo
        cv2.line(frame, (0, self.ALARM_LINE_Y), (width_img, self.ALARM_LINE_Y), self.COLOR_WARN, 2)
        cv2.putText(frame, "BAO DONG", (width_img - 150, self.ALARM_LINE_Y - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLOR_WARN, 2)

        # 3. Chạy AI
        results = self.model(frame, conf=config.AI_CONF_THRESHOLD, verbose=False)
        
        max_water_level = 0.0
        status = "AN_TOAN"
        
        found_flood = False

        for r in results:
            boxes = r.boxes
            for box in boxes:
                found_flood = True
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # --- GỌI HÀM TÍNH TOÁN MỚI ---
                # Truyền mép trên của vùng nước (y1) vào hàm tính
                current_cm = self.calculate_water_level(y1, height_img)
                
                # Cập nhật mức nước cao nhất phát hiện được
                if current_cm > max_water_level:
                    max_water_level = current_cm

                # Kiểm tra vượt ngưỡng (So sánh y1 với y_line)
                is_danger = y1 < self.ALARM_LINE_Y
                
                color = self.COLOR_WARN if is_danger else self.COLOR_SAFE
                
                # Vẽ khung
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Hiển thị số đo ngay tại khung
                label = f"Nuoc: {current_cm}cm"
                if is_danger: label += " !!!"
                
                cv2.putText(frame, label, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Nếu phát hiện nguy hiểm, gán trạng thái
                if is_danger:
                    status = "NGUY_HIEM"

        # Logic phụ: Nếu AI không bắt được gì, trả về mức 0
        if not found_flood:
            max_water_level = 0.0

        # Cập nhật trạng thái CANH_BAO nếu gần chạm vạch (Logic phụ trợ)
        if status == "AN_TOAN" and max_water_level > 0:
            # Tính ra cm của vạch báo động
            alarm_cm = self.calculate_water_level(self.ALARM_LINE_Y, height_img)
            # Nếu còn cách vạch 50cm thì báo Cảnh báo sớm
            if (alarm_cm - 50) < max_water_level < alarm_cm:
                status = "CANH_BAO"

        # Hiển thị tổng quan góc trái trên
        cv2.putText(frame, f"MAX: {max_water_level}cm | {status}", (60, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        return max_water_level, status, frame