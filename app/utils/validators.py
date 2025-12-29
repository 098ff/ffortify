import re
from datetime import datetime
from app.utils.const import VALID_BANKS, MONTH_MAP, THAI_MONTHS
from app.utils.date_time import parse_month_year

def validate_billing_period(billing_str, expected_months):
    """เช็คว่าจำนวนเดือนในข้อความ ตรงกับตัวเลขที่แจ้งไหม"""
    if "-" in billing_str or "ถึง" in billing_str:
        parts = re.split(r'\s*-\s*|\s*ถึง\s*', billing_str)
        if len(parts) >= 2:
            start_data = parse_month_year(parts[0])
            end_data = parse_month_year(parts[1])

            if start_data and end_data:
                start_m, start_y = start_data
                end_m, end_y = end_data
                diff_months = ((end_y * 12) + end_m) - ((start_y * 12) + start_m) + 1
                
                if diff_months != expected_months:
                    raise ValueError(f"⚠️ จำนวนเดือนไม่ตรงกัน!\nแจ้งจ่าย **{expected_months} เดือน**\nแต่นับช่วงเวลาได้ **{diff_months} เดือน**")
                return

    found_count = 0
    for m in MONTH_MAP.keys():
        if m in billing_str: found_count += 1
    
    if expected_months > 1 and found_count == 1:
         raise ValueError(f"⚠️ ข้อมูลไม่ชัดเจน!\nแจ้งจ่าย **{expected_months} เดือน** แต่ระบุมาแค่เดือนเดียว\n(ถ้าระบุเป็นช่วง ให้ใช้ขีดคั่น เช่น 'ม.ค. 68 - มี.ค. 68')")

def validate_slip_format(msg):
    """ตรวจสอบ Format ข้อความ #โอน (แบบแยกบรรทัด)"""
    # แยกบรรทัด และลบ empty line ทิ้ง
    lines = [line.strip() for line in msg.split('\n') if line.strip()]

    # Format ที่คาดหวัง:
    # 0: #โอน
    # 1: ชื่อเล่น
    # 2: จำนวนเงิน
    # 3: จำนวนเดือน
    # 4: ช่วงเดือน
    
    if len(lines) < 5: 
        raise ValueError("❌ ข้อมูลไม่ครบถ้วน! กรุณาพิมพ์แยกบรรทัดตามตัวอย่าง")

    nickname = lines[1]
    
    try: 
        amount = float(lines[2])
    except: 
        raise ValueError("❌ 'จำนวนเงิน' ต้องเป็นตัวเลข (บรรทัดที่ 3)")
        
    try: 
        months_count = int(lines[3])
    except: 
        raise ValueError("❌ 'จำนวนเดือน' ต้องเป็นตัวเลขจำนวนเต็ม (บรรทัดที่ 4)")

    billing_str = lines[4]
    
    # ตรวจสอบช่วงเดือน
    validate_billing_period(billing_str, months_count)

    return {
        "nickname": nickname,
        "amount": amount,
        "months": months_count,
        "billing": billing_str
    }