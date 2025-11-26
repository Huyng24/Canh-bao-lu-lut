# file radio, Nơi xử lý gửi tín hiệu khẩn cấp.

import time

def send_emergency_signal(muc_nuoc, trang_thai):
    """
    Gửi tín hiệu qua module LoRa/RF tới thiết bị B.
    """
    print("\n" + "="*40)
    print(f"🚨 [RADIO KÍCH HOẠT] GỬI TÍN HIỆU KHẨN CẤP!")
    print(f"   - Mực nước: {muc_nuoc} cm")
    print(f"   - Cảnh báo: {trang_thai}")
    print(f"   - Hành động: Kích hoạt còi hú tại Trạm B")
    print("="*40 + "\n")
    
    # Giả lập độ trễ khi gửi sóng vô tuyến (khoảng 0.5s)
    time.sleep(0.5)