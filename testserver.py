import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import os
import time
import streamlit.components.v1 as components # Để nhúng Video

# --- CẤU HÌNH HỆ THỐNG (Khớp với config.py ở Edge) ---
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "lu_lut/tram_01/data"  # <--- Đã sửa cho đúng topic
LOG_FILE = "flood_log.csv"

# Link xem video qua WebRTC (Do MediaMTX cung cấp)
VIDEO_URL = "http://localhost:8889/live" 

# --- CẤU HÌNH GIAO DIỆN WEB ---
st.set_page_config(
    page_title="Hệ thống Cảnh Báo Lũ",
    page_icon="🌊",
    layout="wide"
)

# --- PHẦN 1: XỬ LÝ MQTT (BACKEND) ---
@st.cache_resource
def start_mqtt_listener():
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[SERVER] Đã kết nối Broker! Đang nghe: {MQTT_TOPIC}")
            client.subscribe(MQTT_TOPIC)
        else:
            print(f"[SERVER] Lỗi kết nối: {rc}")

    def on_message(client, userdata, msg):
        try:
            payload_str = msg.payload.decode()
            data = json.loads(payload_str)
            
            # --- CHUẨN HÓA DỮ LIỆU ---
            # Chuyển đổi tên trường từ Edge sang tên chuẩn để lưu file
            record = {
                "timestamp": data.get("timestamp"),
                "device_id": data.get("device_id"),
                "water_level": data.get("water_level"), # Edge gửi water_level
                "status": data.get("status"),           # Edge gửi status
                "mode": data.get("mode", "ONLINE")
            }
            
            save_data_to_csv(record)
            
        except Exception as e:
            print(f"[LỖI] {e}")

    # Sử dụng Callback version 2 cho phù hợp với paho-mqtt mới
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"[CRITICAL] Không thể kết nối MQTT: {e}")
        return None

def save_data_to_csv(data_dict):
    df_new = pd.DataFrame([data_dict])
    if not os.path.exists(LOG_FILE):
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode='a', header=False, index=False)

# --- PHẦN 2: GIAO DIỆN DASHBOARD ---

# Khởi động MQTT (Chạy 1 lần)
start_mqtt_listener()

st.title("🌊 TRUNG TÂM GIÁM SÁT LŨ LỤT (EDGE AI)")
st.markdown(f"**Trạng thái Server:** Đang lắng nghe tại `{MQTT_BROKER}` | **Topic:** `{MQTT_TOPIC}`")
st.divider()

# Đọc dữ liệu mới nhất
if os.path.exists(LOG_FILE):
    try:
        df = pd.read_csv(LOG_FILE)
        df = df.sort_values(by="timestamp", ascending=False)
    except:
        df = pd.DataFrame()
else:
    df = pd.DataFrame()

# Lấy thông số mới nhất để hiển thị
latest_level = 0.0
latest_status = "CHỜ DỮ LIỆU..."
latest_time = "--:--:--"

if not df.empty:
    latest = df.iloc[0]
    latest_level = latest.get("water_level", 0)
    latest_status = latest.get("status", "UNKNOWN")
    latest_time = latest.get("timestamp", "--")

# --- HIỂN THỊ CẢNH BÁO ---
if latest_status == "NGUY_HIEM":
    st.error(f"🚨 CẢNH BÁO LŨ KHẨN CẤP! Mực nước: {latest_level}cm", icon="🚨")
elif latest_status == "CANH_BAO":
    st.warning(f"⚠️ Nước đang dâng cao! Mực nước: {latest_level}cm", icon="⚠️")
else:
    st.success(f"✅ An toàn. Mực nước ổn định.", icon="✅")

# --- BỐ CỤC CHÍNH ---
col1, col2 = st.columns([1.5, 1])

with col1:
    st.subheader("🎥 Camera Trực Tiếp (RTSP/WebRTC)")
    # Nhúng Iframe để xem video từ MediaMTX (Cổng 8889)
    # Đây là phần quan trọng nhất để xem được video trên web
    components.iframe(src=VIDEO_URL, height=400, scrolling=False)

with col2:
    st.subheader("📊 Số Liệu Thời Gian Thực")
    
    # Hiển thị số to
    st.metric(label="Mực nước hiện tại (cm)", value=latest_level, delta=f"{latest_status}")
    st.metric(label="Cập nhật lần cuối", value=latest_time)
    
    st.write("---")
    st.write("📈 **Biểu đồ mực nước (30 bản tin gần nhất)**")
    if not df.empty:
        # Lấy 30 dòng mới nhất, đảo ngược lại để vẽ theo thời gian từ trái qua phải
        chart_data = df.head(30).iloc[::-1]
        st.line_chart(chart_data, x="timestamp", y="water_level")

# --- BẢNG LỊCH SỬ ---
st.subheader("📋 Nhật ký dữ liệu")
st.dataframe(df, use_container_width=True, height=200)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Công cụ")
    if st.button("🗑️ Xóa dữ liệu cũ"):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            st.rerun()

# Tự động refresh trang mỗi 2 giây để cập nhật số liệu và video
time.sleep(2)
st.rerun()