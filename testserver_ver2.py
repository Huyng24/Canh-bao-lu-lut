# Giao diện web hiển thị dashboard

import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import json
import os
import time
import base64
import cv2
import numpy as np
import queue 

# --- CẤU HÌNH HỆ THỐNG ---
MQTT_BROKER = "localhost" 
MQTT_PORT = 1883
MQTT_TOPIC_DATA = "lu_lut/tram_01/data"
MQTT_TOPIC_IMAGE = "lu_lut/tram_01/image" 

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(CURRENT_DIR, "flood_log.csv")

# --- [FIX 1] GIỚI HẠN HÀNG ĐỢI (CHỐNG TRÀN RAM) ---
# Chỉ cho phép lưu tối đa 100 gói tin chờ xử lý. 
# Nếu vượt quá, nó sẽ tự động bị chặn hoặc drop.
if 'GLOBAL_QUEUE' not in globals():
    globals()['GLOBAL_QUEUE'] = queue.Queue(maxsize=100) 

# --- [FIX 2] DỌN DẸP KHI F5 (REFRESH) ---
# Mỗi lần Web load lại, xóa sạch hàng đợi cũ để tránh bị "ngộp" dữ liệu cũ
mq = globals()['GLOBAL_QUEUE']
while not mq.empty():
    try: mq.get_nowait()
    except: pass

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Hệ thống Cảnh Báo Lũ Thông Minh",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS GIAO DIỆN ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.css-1r6slb0.e1tzin5v2 {
        background-color: white; border-radius: 10px; padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;
    }
    img {
        border-radius: 10px;
        border: 4px solid #4CAF50; 
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        width: 100%;
    }
    h1 { color: #0d47a1; font-family: 'Helvetica', sans-serif; text-align: center; margin-bottom: 20px; }
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: bold; }
    .footer-status { font-size: 0.8rem; color: #666; text-align: right; margin-top: 20px; }
    [data-testid="stDataFrame"] { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- LOAD DATA ---
if "data" not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            df_old = pd.read_csv(LOG_FILE)
            st.session_state["data"] = df_old.to_dict('records')
        except: st.session_state["data"] = []
    else: st.session_state["data"] = []

if "last_image" not in st.session_state: st.session_state["last_image"] = None
if "latest_info" not in st.session_state: 
    if len(st.session_state["data"]) > 0:
        last_item = st.session_state["data"][-1]
        st.session_state["latest_info"] = {
            "timestamp": str(last_item.get("timestamp", "--")), 
            "water_level": last_item.get("water_level", 0), 
            "status": last_item.get("status", "UNKNOWN"), 
            "mode": last_item.get("mode", "ONLINE")
        }
    else:
        st.session_state["latest_info"] = {
            "timestamp": "--:--:--", "water_level": 0.0, 
            "status": "ĐANG KẾT NỐI...", "mode": "ONLINE"
        }

# --- MQTT SETUP ---
def on_message(client, userdata, msg):
    try:
        q = globals()['GLOBAL_QUEUE']
        
        # --- [FIX 3] CHIẾN THUẬT DROP FRAME (QUAN TRỌNG) ---
        # Nếu hàng đợi đầy, VỨT BỎ gói tin cũ nhất để nhét gói mới vào.
        # Điều này đảm bảo Web luôn hiển thị cái MỚI NHẤT, không bị lag bởi cái cũ.
        if q.full():
            try:
                q.get_nowait() # Vứt bỏ cái cũ nhất
            except: pass
            
        q.put_nowait((msg.topic, msg.payload))
    except: pass

@st.cache_resource
def setup_mqtt():
    def on_connect(client, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print("✅ [WEB] Kết nối Broker thành công!")
            client.subscribe([(MQTT_TOPIC_DATA, 0), (MQTT_TOPIC_IMAGE, 0)])
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e: print(f"Lỗi MQTT: {e}")
    return client

setup_mqtt()

def save_data_to_csv(data_dict):
    try:
        df_new = pd.DataFrame([data_dict])
        if not os.path.exists(LOG_FILE): df_new.to_csv(LOG_FILE, index=False)
        else: df_new.to_csv(LOG_FILE, mode='a', header=False, index=False)
    except: pass

# --- LAYOUT ---
st.markdown("<h1>🌊 TRUNG TÂM GIÁM SÁT & CẢNH BÁO LŨ LỤT</h1>", unsafe_allow_html=True)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: st.markdown("**🕒 Cập nhật lúc**"); time_placeholder = st.empty()
with col_m2: st.markdown("**📏 Mực nước (cm)**"); level_placeholder = st.empty()
with col_m3: st.markdown("**📡 Chế độ hoạt động**"); mode_placeholder = st.empty()
with col_m4: st.markdown("**🛡️ Trạng thái**"); status_placeholder = st.empty()

st.write("") 

col_left, col_right = st.columns([1.5, 1])
with col_left:
    st.subheader("🎥 Camera AI (Real-time)")
    image_placeholder = st.empty()
    image_placeholder.info("Đang chờ tín hiệu hình ảnh...")

with col_right:
    st.subheader("📈 Xu hướng mực nước")
    chart_placeholder = st.empty()
    stats_placeholder = st.empty()

st.write("")
with st.expander("📋 Xem chi tiết Nhật ký dữ liệu (Log)", expanded=True): 
    log_placeholder = st.empty()

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9046/9046043.png", width=100)
    st.header("⚙️ Điều khiển")
    if st.button("🗑️ Xóa toàn bộ lịch sử", type="primary"):
        if os.path.exists(LOG_FILE):
            try:
                os.remove(LOG_FILE)
                st.session_state["data"] = []
                st.toast("Đã xóa dữ liệu!", icon="🗑️")
                time.sleep(1)
            except: st.error("Lỗi xóa file")
    st.divider()
    st.text(f"Broker: {MQTT_BROKER}")
    st.caption("Phiên bản v2.3 - Anti-Lag Optimized")

st.markdown("""<div class="footer-status">Server đang lắng nghe... (Live Update)</div>""", unsafe_allow_html=True)

# --- VÒNG LẶP CHÍNH ---
while True:
    mq = globals()['GLOBAL_QUEUE']
    
    # [FIX 4] Xử lý tối đa 20 tin mỗi lần lặp để tránh treo giao diện
    # Nếu tin đến nhiều hơn khả năng xử lý, queue drop frame sẽ lo phần còn lại
    process_count = 0
    while not mq.empty() and process_count < 20:
        try:
            topic, payload = mq.get_nowait()
            process_count += 1
            
            if topic == MQTT_TOPIC_DATA:
                data = json.loads(payload.decode())
                save_data_to_csv(data)
                
                st.session_state["data"].append(data)
                # Giới hạn RAM xuống 2000 dòng để nhẹ máy
                if len(st.session_state["data"]) > 2000: 
                    st.session_state["data"].pop(0)
                
                st.session_state["latest_info"] = {
                    "timestamp": data.get("timestamp", "").split('T')[-1].split('.')[0],
                    "water_level": data.get("water_level", 0),
                    "status": data.get("status", "UNKNOWN"),
                    "mode": data.get("mode", "ONLINE")
                }

            elif topic == MQTT_TOPIC_IMAGE:
                img_bytes = base64.b64decode(payload)
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    st.session_state["last_image"] = frame
        except: pass

    # Render UI
    info = st.session_state["latest_info"]
    time_placeholder.info(f"{info['timestamp']}")
    level_placeholder.metric(label="Level", value=f"{info['water_level']}", label_visibility="collapsed")
    
    if info['mode'] == "ONLINE": mode_placeholder.success("ONLINE")
    else: mode_placeholder.warning("OFFLINE")

    s_color = "green"
    s_icon = "✅"
    if info['status'] == "NGUY_HIEM": s_color, s_icon = "red", "🚨"
    elif info['status'] == "CANH_BAO": s_color, s_icon = "orange", "⚠️"

    status_placeholder.markdown(f"""
        <div style="background-color: {s_color}; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;">
            {s_icon} {info['status']}
        </div>
    """, unsafe_allow_html=True)

    if st.session_state["last_image"] is not None:
        st.markdown(f"""<style>img {{ border: 4px solid {s_color} !important; }}</style>""", unsafe_allow_html=True)
        image_placeholder.image(st.session_state["last_image"], channels="RGB", use_container_width=True)

    if len(st.session_state["data"]) > 0:
        df_mem = pd.DataFrame(st.session_state["data"])
        chart_placeholder.area_chart(df_mem.tail(50)[["timestamp", "water_level"]].set_index("timestamp"), color="#29b5e8" if info['status'] == "AN_TOAN" else "#ff4b4b")
        stats_placeholder.info(f"Max: {df_mem['water_level'].max()} cm | Min: {df_mem['water_level'].min()} cm")

        # Log Dataframe
        log_placeholder.dataframe(
            df_mem.sort_values(by="timestamp", ascending=False), 
            use_container_width=True, 
            height=600,
            column_config={
                "timestamp": "Thời gian",
                "water_level": st.column_config.NumberColumn("Mực nước (cm)", format="%.1f"),
                "status": "Cảnh báo",
                "mode": "Chế độ gửi"
            }
        )

    # Sleep hợp lý để giảm tải CPU
    time.sleep(0.05)