import time
import sys
import cv2
import json
import numpy as np
import os

# --- [FIX LỖI QUAN TRỌNG] LẤY ĐƯỜNG DẪN TUYỆT ĐỐI ---
# Lấy đường dẫn thư mục chứa file benchmark.py này
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Ghép với tên file video
VIDEO_PATH = os.path.join(CURRENT_DIR, "test_lu.mp4")

# --- CẤU HÌNH ---
DURATION_TEST = 10 

print(f"📊 ĐANG CHẠY BENCHMARK SO SÁNH EDGE vs CLOUD...")
print(f"📍 Đang tìm video tại: {VIDEO_PATH}")

# Tự động chọn nguồn
if os.path.exists(VIDEO_PATH):
    VIDEO_SOURCE = VIDEO_PATH
    SOURCE_NAME = "File Video (test_lu.mp4)"
    print("✅ Đã tìm thấy file video!")
else:
    VIDEO_SOURCE = 0 
    SOURCE_NAME = "Webcam Laptop (Do không thấy file video)"
    print("⚠️ Không thấy file video -> Chuyển sang dùng Webcam.")

print("-" * 50)

def simulate_cloud_system(source):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("❌ Lỗi: Không mở được nguồn Cloud!")
        return 0, 0

    total_bytes = 0
    start_time = time.time()
    frame_count = 0
    
    while (time.time() - start_time) < DURATION_TEST:
        ret, frame = cap.read()
        if not ret: break
        
        # Cloud: Gửi ảnh to (Quality 90)
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        total_bytes += len(buffer)
        frame_count += 1
        time.sleep(0.03) 
        
    cap.release()
    return total_bytes, frame_count

def simulate_edge_system(source):
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print("❌ Lỗi: Không mở được nguồn Edge!")
        return 0, 0

    total_bytes = 0
    start_time = time.time()
    frame_count = 0
    
    while (time.time() - start_time) < DURATION_TEST:
        ret, frame = cap.read()
        if not ret: break
        
        # Edge: Gửi JSON + Ảnh nhỏ
        result = {"val": 150.5, "stt": "NGUY_HIEM"}
        json_bytes = len(json.dumps(result))
        
        frame_small = cv2.resize(frame, (480, 360))
        _, buffer = cv2.imencode('.jpg', frame_small, [cv2.IMWRITE_JPEG_QUALITY, 60])
        image_bytes = len(buffer)
        
        total_bytes += (json_bytes + image_bytes)
        frame_count += 1
        time.sleep(0.06) 
        
    cap.release()
    return total_bytes, frame_count

# --- CHẠY TEST ---
print("1️⃣  Đang đo hệ thống CLOUD...")
bytes_cloud, frames_cloud = simulate_cloud_system(VIDEO_SOURCE)

print("2️⃣  Đang đo hệ thống EDGE...")
bytes_edge, frames_edge = simulate_edge_system(VIDEO_SOURCE)

# --- TÍNH TOÁN ---
if frames_cloud == 0 or frames_edge == 0:
    print("\n❌ LỖI: Vẫn không đọc được khung hình nào! (File video bị lỗi codec?)")
else:
    mb_cloud = bytes_cloud / (1024 * 1024)
    mb_edge = bytes_edge / (1024 * 1024)
    # Tránh chia cho 0 nếu file quá ngắn
    bw_cloud = mb_cloud/DURATION_TEST if DURATION_TEST > 0 else 0
    bw_edge = mb_edge/DURATION_TEST if DURATION_TEST > 0 else 0

    print(f"\n✅ KẾT QUẢ ĐO TRONG {DURATION_TEST} GIÂY:")
    print("-" * 65)
    print(f"{'CHỈ SỐ':<20} | {'CLOUD SYSTEM':<20} | {'EDGE SYSTEM':<20}")
    print("-" * 65)
    print(f"{'Tổng dung lượng':<20} | {mb_cloud:.2f} MB {'':<10} | {mb_edge:.2f} MB")
    print(f"{'Băng thông TB':<20} | {bw_cloud:.2f} MB/s {'':<10} | {bw_edge:.2f} MB/s {'':<10}")
    print(f"{'Số khung hình':<20} | {frames_cloud} frames {'':<11} | {frames_edge} frames")
    print("-" * 65)

    if mb_edge > 0:
        ratio = mb_cloud / mb_edge
        print(f"🏆 KẾT LUẬN: Edge AI tiết kiệm gấp {ratio:.1f} LẦN so với Cloud!")