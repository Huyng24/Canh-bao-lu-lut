import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import os
import time
import streamlit.components.v1 as components 

# --- CẤU HÌNH HỆ THỐNG ---
MQTT_BROKER = "10.216.77.109"
MQTT_PORT = 1883
MQTT_TOPIC = "lu_lut/tram_01/data"
LOG_FILE = "flood_log.csv"
VIDEO_URL = "http://10.216.77.109:8889/live" 

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Hệ thống Cảnh Báo Lũ Thông Minh",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS LÀM ĐẸP GIAO DIỆN ---
st.markdown("""
    <style>
    /* Chỉnh font và màu nền tổng thể */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Style cho các Card (Khung chứa số liệu) */
    div.css-1r6slb0.e1tzin5v2 {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid #e0e0e0;
    }

    /* Style cho khung Video */
    iframe {
        border-radius: 10px;
        border: 2px solid #4CAF50; /* Viền xanh mặc định */
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Tiêu đề Dashboard */
    h1 {
        color: #0d47a1;
        font-family: 'Helvetica', sans-serif;
        text-align: center;
        margin-bottom: 20px;
    }

    /* Metric (Số đo) */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Trạng thái kết nối ở footer */
    .footer-status {
        font-size: 0.8rem;
        color: #666;
        text-align: right;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# --- PHẦN 1: XỬ LÝ MQTT ---
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
            print(f"📥 [DEBUG] Web nhận được tin: {payload_str}")
            data = json.loads(payload_str)
            record = {
                "timestamp": data.get("timestamp"),
                "device_id": data.get("device_id"),
                "water_level": data.get("water_level"),
                "status": data.get("status"),
                "mode": data.get("mode", "ONLINE")
            }
            save_data_to_csv(record)
        except Exception as e:
            print(f"[LỖI] {e}")

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

# Khởi động MQTT
start_mqtt_listener()

# --- PHẦN 2: XỬ LÝ DỮ LIỆU HIỂN THỊ ---
if os.path.exists(LOG_FILE):
    try:
        df = pd.read_csv(LOG_FILE)
        df = df.sort_values(by="timestamp", ascending=False)
    except:
        df = pd.DataFrame()
else:
    df = pd.DataFrame()

# Lấy thông số mới nhất
latest_level = 0.0
latest_status = "ĐANG CHỜ..."
latest_time = "--:--:--"
latest_mode = "ONLINE"

if not df.empty:
    latest = df.iloc[0]
    latest_level = latest.get("water_level", 0)
    latest_status = latest.get("status", "UNKNOWN")
    latest_time = latest.get("timestamp", "--").split('T')[-1].split('.')[0] # Lấy giờ cho gọn
    latest_mode = latest.get("mode", "ONLINE")

# Xác định màu sắc giao diện dựa trên trạng thái
status_color = "green"
status_icon = "✅"
alert_msg = "An toàn"

if latest_status == "NGUY_HIEM":
    status_color = "red"
    status_icon = "🚨"
    alert_msg = "NGUY HIỂM - VƯỢT MỨC"
elif latest_status == "CANH_BAO":
    status_color = "orange"
    status_icon = "⚠️"
    alert_msg = "CẢNH BÁO - NƯỚC DÂNG"

# --- PHẦN 3: GIAO DIỆN DASHBOARD ---

# 3.1 Header
st.markdown("<h1>🌊 TRUNG TÂM GIÁM SÁT & CẢNH BÁO LŨ LỤT</h1>", unsafe_allow_html=True)

# 3.2 Key Metrics (Hàng ngang trên cùng)
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(f"**🕒 Cập nhật lúc**")
    st.info(f"{latest_time}")

with col_m2:
    st.markdown(f"**📏 Mực nước (cm)**")
    st.metric(label="Level", value=f"{latest_level}", delta=None, label_visibility="collapsed")

with col_m3:
    st.markdown(f"**📡 Chế độ hoạt động**")
    if latest_mode == "ONLINE":
        st.success("ONLINE (Realtime)")
    else:
        st.warning("OFFLINE (History)")

with col_m4:
    st.markdown(f"**🛡️ Trạng thái**")
    st.markdown(f"""
        <div style="background-color: {status_color}; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
            {status_icon} {latest_status}
        </div>
    """, unsafe_allow_html=True)

st.write("") # Spacer

# 3.3 Main Content (Video & Chart)
col_left, col_right = st.columns([1.5, 1]) # Tỉ lệ 60% - 40%

with col_left:
    st.subheader("🎥 Camera Trực Tiếp")
    # Viền video sẽ đổi màu theo trạng thái báo động
    st.markdown(f"""
    <style>
    iframe {{
        border: 4px solid {status_color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Nhúng Video
    components.iframe(src=VIDEO_URL, height=450, scrolling=False)
    st.caption(f"🔗 Nguồn phát: {VIDEO_URL} (MediaMTX)")

with col_right:
    st.subheader("📈 Xu hướng mực nước")
    
    if not df.empty:
        # Lấy 50 điểm dữ liệu gần nhất để vẽ biểu đồ cho mượt
        chart_data = df.head(50).iloc[::-1]
        
        # Vẽ biểu đồ vùng (Area Chart) 
        st.area_chart(
            chart_data, 
            x="timestamp", 
            y="water_level",
            color="#29b5e8" if latest_status == "AN_TOAN" else "#ff4b4b"
        )
        
        # Thống kê nhanh
        st.info(f"Mức nước cao nhất (24h): **{df['water_level'].max()} cm**")
        st.info(f"Mức nước thấp nhất (24h): **{df['water_level'].min()} cm**")
    else:
        st.write("Chưa có dữ liệu để vẽ biểu đồ.")

# 3.4 Data Log (Dạng xổ xuống)
st.write("")
with st.expander("📋 Xem chi tiết Nhật ký dữ liệu (Log)", expanded=False):
    st.dataframe(
        df, 
        use_container_width=True, 
        height=300,
        column_config={
            "timestamp": "Thời gian",
            "water_level": st.column_config.NumberColumn("Mực nước (cm)", format="%.1f"),
            "status": "Cảnh báo",
            "mode": "Chế độ gửi"
        }
    )

# 3.5 Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9046/9046043.png", width=100)
    st.header("⚙️ Điều khiển")
    st.write("Quản lý dữ liệu hệ thống")
    
    if st.button("🗑️ Xóa toàn bộ lịch sử", type="primary"):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            st.toast("Đã xóa dữ liệu thành công!", icon="🗑️")
            time.sleep(1)
            st.rerun()
            
    st.divider()
    st.markdown("### ℹ️ Thông tin Trạm")
    st.text(f"Broker: {MQTT_BROKER}")
    st.text(f"Topic: {MQTT_TOPIC}")
    st.caption("Phiên bản v2.0 - Edge AI Dashboard")

# Footer status
st.markdown(f"""
    <div class="footer-status">
        Server đang lắng nghe... (Tự động cập nhật sau 2s)
    </div>
""", unsafe_allow_html=True)

# Auto refresh
time.sleep(2)
st.rerun()
#