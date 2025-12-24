# file test giả lập module AI 

import random
import time
from config import LEVEL_ALARM_1, LEVEL_ALARM_2

def get_ai_result():
    """
    Hàm này mô phỏng kết quả trả về từ Model AI.
    Output: (muc_nuoc, trang_thai)
    """
    # Giả lập mực nước dao động
    water_level = round(random.uniform(100, 250), 1)
    
    status = "BINH_THUONG"
    if water_level >= LEVEL_ALARM_2:
        status = "NGUY_HIEM"
    elif water_level >= LEVEL_ALARM_1:
        status = "CANH_BAO"
        
    # Giả lập thời gian xử lý của AI (vd: mất 0.1s)
    time.sleep(0.1)
    
    return water_level, status