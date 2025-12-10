# testserver.py
import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import time
import base64
import cv2
import numpy as np
import queue  # Thư viện hàng đợi
import config

# --- CẤU HÌNH ---
st.set_page_config(page_title="Hệ Thống Cảnh Báo Lũ", layout="wide")

# CSS tùy chỉnh
st.markdown("""
    <style>
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
        .stAlert { padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- [KHẮC PHỤC LỖI] KHỞI TẠO GLOBAL QUEUE ---
# Để biến này ở ngoài cùng, không thuộc về session nào cả
# Giúp luồng MQTT (Background) có thể truy cập được
if 'GLOBAL_QUEUE' not in globals():
    globals()['GLOBAL_QUEUE'] = queue.Queue()

# --- KHỞI TẠO STATE ---
if "data" not in st.session_state:
    st.session_state["data"] = []
if "last_image" not in st.session_state:
    st.session_state["last_image"] = None
if "latest_info" not in st.session_state:
    st.session_state["latest_info"] = {"level": 0, "status": "DANG_KET_NOI..."}

# --- HÀM XỬ LÝ KHI CÓ TIN NHẮN (CHẠY NGẦM) ---
def on_message(client, userdata, msg):
    # Ở đây KHÔNG ĐƯỢC dùng st.session_state
    # Chỉ đẩy dữ liệu vào biến toàn cục GLOBAL_QUEUE
    try:
        topic = msg.topic
        payload = msg.payload
        # Đẩy vào hàng đợi toàn cục
        globals()['GLOBAL_QUEUE'].put((topic, payload))
    except Exception as e:
        # Không dùng st.error() ở đây vì sẽ gây lỗi Context
        print(f"Lỗi queue: {e}")

# --- KẾT NỐI MQTT ---
@st.cache_resource
def setup_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.subscribe([(config.MQTT_TOPIC_DATA, 0), (config.MQTT_TOPIC_IMAGE, 0)])
        client.loop_start()
        return client
    except Exception as e:
        return None

client = setup_mqtt()

# --- GIAO DIỆN WEB ---
st.title("🌊 HỆ THỐNG GIÁM SÁT LŨ LỤT (EDGE AI)")

col_video, col_info = st.columns([2, 1])

with col_video:
    st.subheader("🎥 Camera AI (Real-time)")
    image_placeholder = st.empty()
    if st.session_state["last_image"] is None:
        image_placeholder.info("Đang chờ tín hiệu hình ảnh từ Edge Device...")

with col_info:
    st.subheader("📊 Thông số hiện tại")
    status_placeholder = st.empty()
    metric_placeholder = st.empty()
    st.divider()
    st.subheader("📈 Biểu đồ lịch sử")
    chart_placeholder = st.empty()

# --- VÒNG LẶP CHÍNH (MAIN LOOP) ---
while True:
    # 1. RÚT TIN NHẮN TỪ GLOBAL QUEUE RA XỬ LÝ
    # Lấy biến toàn cục ra dùng
    mq = globals()['GLOBAL_QUEUE']
    
    # Rút hết tin trong hàng đợi để cập nhật cho kịp
    while not mq.empty():
        try:
            topic, payload = mq.get_nowait()
            
            # A. Xử lý Dữ liệu JSON
            if topic == config.MQTT_TOPIC_DATA:
                data = json.loads(payload.decode())
                st.session_state["data"].append(data)
                if len(st.session_state["data"]) > 50:
                    st.session_state["data"].pop(0)
                
                st.session_state["latest_info"] = {
                    "level": data["water_level"],
                    "status": data["status"]
                }
                
            # B. Xử lý Hình ảnh Base64
            elif topic == config.MQTT_TOPIC_IMAGE:
                img_bytes = base64.b64decode(payload)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    st.session_state["last_image"] = frame
        except:
            pass

    # 2. VẼ LẠI GIAO DIỆN
    if st.session_state["last_image"] is not None:
        image_placeholder.image(st.session_state["last_image"], channels="RGB", use_container_width=True)

    info = st.session_state["latest_info"]
    level = info["level"]
    status = info["status"]

    status_color = "gray"
    if status == "AN_TOAN": status_color = "green"
    elif status == "CANH_BAO": status_color = "orange"
    elif status == "NGUY_HIEM": status_color = "red"

    status_placeholder.markdown(f"""
        <div style="background-color:{status_color}; padding:15px; border-radius:10px; color:white; text-align:center;">
            <h2 style="margin:0;">{status}</h2>
        </div>
    """, unsafe_allow_html=True)

    metric_placeholder.metric("Mực nước hiện tại", f"{level} cm")

    if len(st.session_state["data"]) > 0:
        df = pd.DataFrame(st.session_state["data"])
        chart_data = df[["timestamp", "water_level"]].copy()
        chart_placeholder.line_chart(chart_data.set_index("timestamp"))

    time.sleep(0.1)