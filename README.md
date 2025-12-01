# 🌊 Hệ Thống Cảnh Báo Lũ Lụt & Giám Sát Thời Gian Thực (Edge Computing)

Dự án IoT tích hợp Edge Computing để giám sát mực nước, phát cảnh báo lũ lụt sớm ngay cả khi mất kết nối mạng (tính năng Store & Forward). Hệ thống tích hợp Camera AI, giao thức MQTT và Web Dashboard trực quan.

## 🚀 Tính Năng Nổi Bật

- **Real-time Monitoring:** Giám sát mực nước và video trực tiếp với độ trễ thấp (< 500ms).
- **Edge Computing Logic:** Xử lý dữ liệu ngay tại biên (Edge Device).
- **Fault Tolerance (Chịu lỗi):**
  - **Store & Forward:** Tự động lưu dữ liệu vào bộ nhớ đệm khi mất mạng và gửi bù ngay khi có mạng lại.
  - **Redundancy:** Tự động kích hoạt cảnh báo qua sóng Radio/LoRa khi Internet bị ngắt (Simulation).
- **Smart Dashboard:** Giao diện Web (Streamlit) tích hợp biểu đồ và video streaming.

## 🛠️ Kiến Trúc Hệ Thống

1.  **Đầu vào (Input):** Camera IP / Điện thoại (RTSP Stream).
2.  **Xử lý trung gian (Middleware):**
    - **FFmpeg:** Chuyển tiếp và tối ưu hóa luồng video.
    - **MediaMTX:** RTSP Server (Phân phối video cho AI và Web).
    - **Mosquitto:** MQTT Broker (Trung chuyển dữ liệu điều khiển).
3.  **Bộ não (Controller):** Python script xử lý logic, đọc cảm biến ảo/thật.
4.  **Đầu ra (Output):** Web Dashboard (Streamlit) & File Log (CSV).

## 📦 Yêu Cầu Cài Đặt

### 1. Phần mềm bắt buộc
- Python 3.8+
- [Mosquitto Broker](https://mosquitto.org/download/)
- [MediaMTX](https://github.com/bluenviron/mediamtx/releases) (RTSP Server)
- [FFmpeg](https://ffmpeg.org/download.html) (Xử lý video)
- App **IP Webcam** (Trên Android) để giả lập Camera.

### 2. Thư viện Python
Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
