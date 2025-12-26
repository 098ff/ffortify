import re
from datetime import datetime, timedelta, timezone
from app.utils.const import MONTH_MAP, THAI_MONTHS

def get_thai_time():
    """คืนค่าเวลาปัจจุบันในโซนเวลาไทย (UTC+7)"""
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz)

def calculate_next_bill_date(start_date, months_to_add):
    """ตัดรอบวันที่ 13 เสมอ"""
    # ใช้เวลาไทยในการคำนวณ
    now = get_thai_time()
    
    # ถ้า start_date เป็น None หรือเป็นอดีตไปแล้ว ให้เริ่มนับจากปัจจุบัน
    if not start_date or start_date.astimezone(timezone(timedelta(hours=7))) < now:
        if now.day > 13:
            # ถ้าเลยวันที่ 13 ไปแล้ว ให้เริ่มนับเดือนหน้า
            year, month = now.year, now.month 
        else:
            year, month = now.year, now.month
    else:
        # ถ้ายอมรับ start_date แบบ naive (ไม่มี timezone) ให้ระวังตรงนี้
        # แต่เพื่อความง่าย เราดึง year/month มาใช้เลย
        year, month = start_date.year, start_date.month

    total_months = month + months_to_add
    new_year = year + (total_months - 1) // 12
    new_month = (total_months - 1) % 12 + 1
    
    # ส่งคืนเป็น datetime object (อาจจะเลือกไม่ใส่ timezone เพื่อให้เซฟลง DB ง่าย หรือใส่ตามต้องการ)
    return datetime(new_year, new_month, 13, 23, 59, 59)

def get_thai_month_year(dt):
    if not dt: return "ยังไม่มีข้อมูล"
    return f"{THAI_MONTHS[dt.month-1]} {dt.year+543-2500}"

def parse_month_year(text):
    """แกะหา (เดือน, ปี) จากข้อความ"""
    found_month = None
    for m_str, m_idx in MONTH_MAP.items():
        if m_str in text:
            found_month = m_idx
            break
    if not found_month: return None

    # หาปี (2 หลัก หรือ 4 หลัก)
    year_match = re.search(r'\d{2,4}', text)
    if year_match:
        year_val = int(year_match.group())
        # แปลงปี พ.ศ. / ค.ศ.
        if year_val < 100: year_val += 2500 # เดาว่าเป็น พ.ศ. 2 หลัก
        if year_val < 2400: year_val += 543 # ถ้าเป็น ค.ศ. ให้บวก 543
    else:
        # ถ้าไม่ระบุปี ให้ใช้ปีปัจจุบัน
        year_val = get_thai_time().year + 543 
        
    return (found_month, year_val)