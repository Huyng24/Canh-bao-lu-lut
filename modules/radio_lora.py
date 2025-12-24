# Nơi xử lý gửi tín hiệu khẩn cấp.
# modules/radio_lora.py

import time
import winsound

last_alert_time = 0

def send_emergency_signal(muc_nuoc, trang_thai):
    """
    Hàm này thực hiện 2 việc:
    1. Phát âm thanh cảnh báo tại chỗ (Laptop).
    2. Gửi tín hiệu LoRa (Giả lập hoặc thật).
    """
    global last_alert_time
    current_time = time.time()

    # Chỉ kích hoạt nếu lần báo trước cách đây hơn 10 giây
    if current_time - last_alert_time > 10.0:
        print("\n" + "="*40)
        print("\n>>> [NGUY HIỂM] KÍCH HOẠT HỆ THỐNG PHẢN ỨNG NHANH <<<")
        
        # 1. Phát âm thanh cảnh báo (Tại chỗ)
        try:
            # SND_ALIAS: Dùng âm thanh hệ thống (giả lập bằng tiếng báo lỗi Windows)
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
            print("🔊 [CÒI HÚ] Đang phát âm thanh cảnh báo trên Laptop...")
        except Exception as e:
            print(f"⚠️ Không thể phát âm thanh: {e}")

        # 2. Gửi tín hiệu Radio/LoRa (Đi xa)
        # (code giả lập in ra màn hình)
        print(f"🚨 [RADIO KÍCH HOẠT] GỬI TÍN HIỆU KHẨN CẤP!")
        print(f"   - Mực nước: {muc_nuoc} cm")
        print(f"   - Cảnh báo: {trang_thai}")
        print(f"   - Hành động: Kích hoạt còi hú tại Trạm B")
        print("="*40 + "\n")
        
        # Cập nhật thời gian
        last_alert_time = current_time
#