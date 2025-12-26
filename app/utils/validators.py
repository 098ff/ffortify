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
    """ตรวจสอบ Format ข้อความ #โอน"""
    parts = msg.split()
    
    bank_index = -1
    found_bank = ""
    for idx, part in enumerate(parts):
        for v_bank in VALID_BANKS:
            if part.lower() == v_bank.lower():
                bank_index = idx
                found_bank = v_bank
                break
        if bank_index != -1: break
            
    if bank_index == -1: raise ValueError(f"❌ ไม่พบชื่อธนาคารที่รองรับ (ต้องเป็น: {', '.join(VALID_BANKS)})")
    if bank_index < 5: raise ValueError("❌ ข้อมูลไม่ครบถ้วน (กรุณาใส่ 'ช่วงเดือน' ด้วย)")

    nickname = parts[1]
    try: amount = float(parts[2])
    except: raise ValueError("❌ 'จำนวนเงิน' ต้องเป็นตัวเลข")
    try: months_count = int(parts[3])
    except: raise ValueError("❌ 'จำนวนเดือน' ต้องเป็นตัวเลขจำนวนเต็ม")

    billing_parts = parts[4:bank_index]
    billing_str = " ".join(billing_parts)
    
    validate_billing_period(billing_str, months_count)

    date_time_parts = parts[bank_index+1:]
    if len(date_time_parts) != 4: raise ValueError("❌ รูปแบบวันเวลาไม่ถูกต้อง (ตัวอย่าง: 26 ม.ค. 68 10:30:00)")

    day_str, month_str, year_str, time_str = date_time_parts
    if month_str not in THAI_MONTHS: raise ValueError(f"❌ ตัวย่อเดือนไม่ถูกต้อง")
    if not re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", time_str): raise ValueError("❌ รูปแบบเวลาไม่ถูกต้อง")

    return {
        "nickname": nickname,
        "amount": amount,
        "months": months_count,
        "billing": billing_str,
        "bank": found_bank,
        "datetime": f"{day_str} {month_str} {year_str} {time_str}"
    }