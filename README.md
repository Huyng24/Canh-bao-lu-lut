# Hệ Thống Cảnh Báo Lũ Lụt Thông Minh (Edge AI Flood Warning System)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-green)
![MQTT](https://img.shields.io/badge/IoT-MQTT-orange)
![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red)
![Architecture](https://img.shields.io/badge/Architecture-Edge%20Computing-purple)

> **Mô tả:** Hệ thống giám sát mực nước và cảnh báo lũ lụt theo thời gian thực sử dụng công nghệ **Edge Computing (Điện toán biên)**. Hệ thống xử lý hình ảnh bằng AI ngay tại thiết bị biên (Laptop/Jetson) thay vì gửi video về Cloud, giúp giảm băng thông, giảm độ trễ và đảm bảo hoạt động ổn định ngay cả khi mất kết nối Internet.

---

## 🚀 Tính năng nổi bật (Key Features)

1.  **AI Giám sát Thời gian thực:** Sử dụng mô hình **YOLOv8** để phát hiện mặt nước.
2.  **Cơ chế "Safety Line" (Vạch An Toàn):** Thiết lập đường ranh giới ảo trên camera. Hệ thống tự động báo động khi mực nước dâng vượt qua vạch kẻ.
3.  **Hoạt động bền bỉ (Fault Tolerance):**
    * **Online:** Gửi dữ liệu và hình ảnh đã xử lý về Web Dashboard qua MQTT.
    * **Offline (Mất mạng):** Tự động lưu dữ liệu vào bộ nhớ đệm (Buffer).
    * **Reconnect (Có mạng lại):** Tự động đồng bộ (Flush) dữ liệu cũ lên Server, không mất gói tin nào.
4.  **Dashboard trực quan:** Giao diện Web (Streamlit) hiển thị Video AI (có vẽ khung cảnh báo), Biểu đồ mực nước lịch sử và Log chi tiết.
5.  **Cảnh báo đa kênh:** Còi hú tại chỗ (Local Siren) + Cảnh báo trên Web (Remote Alert).

---

## 🛠️ Kiến trúc hệ thống (System Architecture)

Hệ thống được thiết kế theo mô hình 3 tầng: **Thiết bị (Device) - Biên (Edge) - Trung tâm (Cloud/Server)**.

### Sơ đồ luồng dữ liệu (Data Flow)

```mermaid
flowchart LR
    CAM(Camera IP/File Video) -->|RTSP| EDGE[Thiết bị Biên - Edge PC]
    
    subgraph EDGE_PROCESS [Xử lý tại Biên]
        direction TB
        AI[AI YOLOv8 Detect]
        LOGIC{Logic Điều khiển}
        BUFFER[(Offline Buffer)]
        LORA[Module Radio/Còi hú]
    end

    EDGE --> AI --> LOGIC
    
    LOGIC -->|Nguy hiểm| LORA
    LOGIC -->|Mất mạng| BUFFER
    LOGIC -->|Có mạng| MQTT[MQTT Broker]
    
    BUFFER -.->|Có mạng lại| MQTT
    
    subgraph SERVER [Server Trung tâm]
        MQTT --> WEB[Web Dashboard]
        WEB --> DB[(File Log CSV)]
    end
