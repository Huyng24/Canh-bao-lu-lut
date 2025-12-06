import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import os
import time
from datetime import datetime

# --- CẤU HÌNH HỆ THỐNG ---
# Nếu cài Mosquitto trên máy này, Broker là 'localhost'
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "flood/alert"
LOG_FILE = "flood_log.csv"

# --- CẤU HÌNH GIAO DIỆN WEB ---
st.set_page_config(
    page_title="Flood Monitoring Center",
    page_icon="🌊",
    layout="wide"
)

# --- PHẦN 1: XỬ LÝ MQTT (CHẠY NGẦM) ---
# Hàm này dùng st.cache_resource để chỉ chạy 1 lần duy nhất khi bật server
# Nó tạo ra một luồng lắng nghe tin nhắn từ Laptop 1 mà không làm đơ giao diện

@st.cache_resource
def start_mqtt_listener():
    """Khởi tạo MQTT Client và lắng nghe tin nhắn"""
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("[SERVER] Đã kết nối tới Broker thành công!")
            client.subscribe(MQTT_TOPIC)
        else:
            print(f"[SERVER] Kết nối thất bại, mã lỗi: {rc}")

    def on_message(client, userdata, msg):
        try:
            # Nhận tin nhắn JSON từ Edge
            payload_str = msg.payload.decode()
            print(f"[NHẬN TIN] {payload_str}")
            
            data = json.loads(payload_str)
            
            # Lưu ngay vào file CSV
            save_data_to_csv(data)
            
        except Exception as e:
            print(f"[LỖI] Không thể xử lý tin nhắn: {e}")

    # Khởi tạo Client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start() # Chạy luồng background
        return client
    except Exception as e:
        print(f"[LỖI CRITICAL] Không thể kết nối Mosquitto: {e}")
        return None

def save_data_to_csv(data_dict):
    """Lưu dữ liệu nhận được vào file CSV"""
    # Tạo DataFrame từ dữ liệu mới
    df_new = pd.DataFrame([data_dict])
    
    # Nếu file chưa tồn tại thì tạo mới kèm header, ngược lại thì ghi nối đuôi (append)
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- PHẦN 2: GIAO DIỆN DASHBOARD (REFRESH LIÊN TỤC) ---

# 1. Khởi động MQTT Listener (Chỉ chạy 1 lần đầu tiên)
client = start_mqtt_listener()

# 2. Tiêu đề Dashboard
st.title("🌊 TRUNG TÂM GIÁM SÁT & CẢNH BÁO LŨ LỤT")
st.markdown("**Môn học:** Hệ thống & Mạng máy tính | **Nhóm:** 11")
st.divider()

# 3. Đọc dữ liệu từ file Log (CSV)
# Mỗi lần Streamlit refresh giao diện, nó sẽ đọc lại file này để cập nhật số liệu mới nhất
if os.path.exists(LOG_FILE):
    try:
        df = pd.read_csv(LOG_FILE)
        # Sắp xếp: Tin mới nhất lên đầu
        df = df.sort_values(by="timestamp", ascending=False)
    except:
        df = pd.DataFrame(columns=["device_id", "timestamp", "level", "message"])
else:
    df = pd.DataFrame(columns=["device_id", "timestamp", "level", "message"])

# 4. Tính toán trạng thái hiện tại
current_status = "AN TOÀN"
status_style = "success" # Màu xanh
alert_msg = ""

if not df.empty:
    # Lấy bản tin mới nhất
    latest_record = df.iloc[0]
    
    # Logic: Nếu tin mới nhất là DANGER -> Hệ thống đang báo động
    if latest_record["level"] == "DANGER":
        current_status = "NGUY HIỂM - CÓ LŨ!"
        status_style = "error" # Màu đỏ
        alert_msg = f"⚠️ CẢNH BÁO: {latest_record['message']} (Lúc: {latest_record['timestamp']})"
    
    # Đếm số lượng cảnh báo nguy hiểm
    danger_count = len(df[df["level"] == "DANGER"])
else:
    danger_count = 0

# 5. Hiển thị Metrics (Các ô chỉ số)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Trạng thái Hệ thống", value=current_status)

with col2:
    st.metric(label="Số lần Cảnh báo Lũ", value=danger_count)

with col3:
    st.metric(label="Thiết bị Edge", value="Online", delta="Kết nối ổn định")

# Hiển thị thông báo lớn nếu đang nguy hiểm
if status_style == "error":
    st.error(alert_msg, icon="🚨")
else:
    st.success("Hiện tại chưa phát hiện dấu hiệu bất thường.", icon="✅")

# 6. Chia cột hiển thị Bảng & Biểu đồ
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("📋 Nhật ký Cảnh báo (Real-time)")
    # Hiển thị bảng dữ liệu đẹp mắt
    st.dataframe(
        df, 
        use_container_width=True,
        column_config={
            "timestamp": "Thời gian",
            "device_id": "Thiết bị",
            "level": "Mức độ",
            "message": "Nội dung cảnh báo"
        }
    )

with col_right:
    st.subheader("📊 Thống kê Mức độ")
    if not df.empty:
        # Vẽ biểu đồ tròn hoặc cột đơn giản đếm số lượng Normal vs Danger
        st.bar_chart(df["level"].value_counts(), color="#ff4b4b")
    else:
        st.info("Chưa có dữ liệu thống kê.")

# 7. Sidebar (Cấu hình & Công cụ)
with st.sidebar:
    st.header("⚙️ Cấu hình Server")
    st.write(f"**MQTT Broker:** {MQTT_BROKER}")
    st.write(f"**Port:** {MQTT_PORT}")
    st.write(f"**Topic:** {MQTT_TOPIC}")
    
    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử dữ liệu"):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            st.rerun() # Tải lại trang ngay lập tức

# 8. Tự động Refresh trang
# Logic: Ngủ 1 giây rồi tải lại trang để cập nhật dữ liệu mới từ CSV
time.sleep(1)
st.rerun()