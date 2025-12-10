# testserverv2.py
import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import time
import base64
import cv2
import numpy as np
import config  # Lấy cấu hình từ file chung

# --- CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Cảnh Báo Lũ", layout="wide")

# CSS tùy chỉnh để giao diện đẹp hơn
st.markdown("""
    <style>
        .stMetric {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 10px;
        }
        .stAlert {
            padding: 10px;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO SESSION STATE (Biến toàn cục của Web) ---
if "data" not in st.session_state:
    st.session_state["data"] = []
if "last_image" not in st.session_state:
    st.session_state["last_image"] = None
if "latest_info" not in st.session_state:
    st.session_state["latest_info"] = {"level": 0, "status": "KHONG_CO_DU_LIEU"}

# --- HÀM XỬ LÝ KHI CÓ TIN NHẮN ĐẾN ---
def on_message(client, userdata, msg):
    topic = msg.topic
    
    # TRƯỜNG HỢP 1: Nhận dữ liệu số (JSON)
    if topic == config.MQTT_TOPIC_DATA:
        try:
            payload = json.loads(msg.payload.decode())
            st.session_state["data"].append(payload)
            # Giữ lại 50 bản tin gần nhất để vẽ biểu đồ cho nhẹ
            if len(st.session_state["data"]) > 50:
                st.session_state["data"].pop(0)
            
            # Cập nhật thông tin mới nhất
            st.session_state["latest_info"] = {
                "level": payload["water_level"],
                "status": payload["status"]
            }
        except: pass

    # TRƯỜNG HỢP 2: Nhận hình ảnh (Base64)
    elif topic == config.MQTT_TOPIC_IMAGE:
        try:
            # Giải mã chuỗi Base64 thành tấm ảnh
            img_bytes = base64.b64decode(msg.payload)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            # Đổi hệ màu từ BGR (OpenCV) sang RGB (Web)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            st.session_state["last_image"] = frame
        except Exception as e:
            print(f"Lỗi giải mã ảnh: {e}")

# --- KẾT NỐI MQTT ---
@st.cache_resource
def setup_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        # Đăng ký nhận cả 2 kênh: Dữ liệu và Hình ảnh
        client.subscribe([(config.MQTT_TOPIC_DATA, 0), (config.MQTT_TOPIC_IMAGE, 0)])
        client.loop_start()
        return client
    except Exception as e:
        st.error(f"Không kết nối được MQTT Broker: {e}")
        return None

client = setup_mqtt()

# --- GIAO DIỆN WEB ---
st.title("🌊 HỆ THỐNG GIÁM SÁT LŨ LỤT (EDGE AI)")

# Chia giao diện làm 2 cột: Trái (Video) - Phải (Thông số)
col_video, col_info = st.columns([2, 1]) # Cột video rộng gấp đôi cột info

with col_video:
    st.subheader("🎥 Camera AI (Real-time)")
    # Tạo một khung trống để chứa ảnh
    image_placeholder = st.empty()
    
    # Nếu chưa có ảnh nào thì hiện thông báo chờ
    if st.session_state["last_image"] is None:
        image_placeholder.info("Đang chờ tín hiệu hình ảnh từ Edge Device...")

with col_info:
    st.subheader("📊 Thông số hiện tại")
    status_placeholder = st.empty()
    metric_placeholder = st.empty()
    
    st.divider()
    st.subheader("📈 Biểu đồ lịch sử")
    chart_placeholder = st.empty()

# --- VÒNG LẶP CẬP NHẬT GIAO DIỆN ---
while True:
    # 1. Cập nhật Ảnh mới nhất vào khung
    if st.session_state["last_image"] is not None:
        image_placeholder.image(st.session_state["last_image"], channels="RGB", use_container_width=True)

    # 2. Cập nhật Trạng thái và Số liệu
    info = st.session_state["latest_info"]
    level = info["level"]
    status = info["status"]

    # Đổi màu cảnh báo
    status_color = "gray"
    if status == "AN_TOAN": status_color = "green"
    elif status == "CANH_BAO": status_color = "orange"
    elif status == "NGUY_HIEM": status_color = "red"

    # Hiển thị Status dạng khung màu
    status_placeholder.markdown(f"""
        <div style="background-color:{status_color}; padding:15px; border-radius:10px; color:white; text-align:center;">
            <h2 style="margin:0;">{status}</h2>
        </div>
    """, unsafe_allow_html=True)

    # Hiển thị số đo
    metric_placeholder.metric("Mực nước hiện tại", f"{level} cm")

    # 3. Vẽ biểu đồ
    if len(st.session_state["data"]) > 0:
        df = pd.DataFrame(st.session_state["data"])
        # Chỉ lấy cột thời gian và mực nước để vẽ
        chart_data = df[["timestamp", "water_level"]].copy()
        chart_placeholder.line_chart(chart_data.set_index("timestamp"))

    # Nghỉ 0.1 giây để giảm tải cho trình duyệt (tạo hiệu ứng 10 FPS)
    time.sleep(0.1)