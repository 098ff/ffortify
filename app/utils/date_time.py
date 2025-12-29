import re
from datetime import datetime, timedelta, timezone
from app.utils.const import MONTH_MAP, THAI_MONTHS

def get_thai_time():
    """คืนค่าเวลาปัจจุบันในโซนเวลาไทย (UTC+7)"""
    tz = timezone(timedelta(hours=7))
    return datetime.now(tz)

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
        # แปลงปีให้เป็น ค.ศ. (AD)
        if year_val < 100: year_val += (2500 - 543) # เช่น 68 -> 2025
        elif year_val > 2400: year_val -= 543       # เช่น 2568 -> 2025
    else:
        # ถ้าไม่ระบุปี ให้ใช้ปีปัจจุบัน (พ.ศ. -> ค.ศ.)
        year_val = datetime.now().year
        
    return (found_month, year_val)

def get_thai_month_year(dt):
    if not dt: return "ยังไม่มีข้อมูล"
    return f"{THAI_MONTHS[dt.month-1]} {dt.year+543-2500}"

def calculate_next_due_date_from_text(billing_str, months_to_add):
    """
    User พิมพ์: "ม.ค." (1 เดือน) -> แปลว่าจ่ายจบเดือน 1 -> Due Date คือ 13 ก.พ.
    User พิมพ์: "ม.ค. - ก.พ." (2 เดือน) -> แปลว่าจ่ายจบเดือน 2 -> Due Date คือ 13 มี.ค.
    """
    clean_txt = billing_str.replace('ถึง', '-').replace(' ', '')
    start_str = clean_txt.split('-')[0]
    
    parsed = parse_month_year(start_str)
    if not parsed: return None
    
    start_month, start_year = parsed # ได้ปี ค.ศ. มาแล้วจาก parse_month_year
    
    # สูตร: เดือนเริ่ม + จำนวนเดือนที่จ่าย = เดือนที่ครบกำหนดรอบหน้า
    # เช่น เริ่มเดือน 1 (ม.ค.) + จ่าย 1 เดือน = เดือน 2 (ก.พ.) -> วันที่ 13
    total_months = start_month + months_to_add
    
    new_year = start_year + (total_months - 1) // 12
    new_month = (total_months - 1) % 12 + 1
    
    return datetime(new_year, new_month, 13, 23, 59, 59)

def calculate_next_bill_date(current_due_date, months_to_add):
    """
    คำนวณ Next Due Date โดยบวกเพิ่มจากของเดิม
    """
    now = get_thai_time().replace(tzinfo=None) # ตัด timezone เพื่อเทียบง่ายๆ
    
    # ถ้าไม่มีข้อมูลเดิม หรือ ของเดิมมันผ่านมานานแล้ว (ขาดส่ง) ให้เริ่มนับจากปัจจุบัน
    if not current_due_date or current_due_date < now:
        # ถ้าวันนี้เลยวันที่ 13 ไปแล้ว ให้เริ่มนับเดือนหน้า
        base_date = now
        if now.day > 13:
            # ขยับไปเดือนหน้า
            if base_date.month == 12:
                year, month = base_date.year + 1, 1
            else:
                year, month = base_date.year, base_date.month + 1
        else:
            year, month = base_date.year, base_date.month
    else:
        # ถ้าจ่ายต่อเนื่อง ให้ใช้ Due Date เดิมเป็นฐาน
        year, month = current_due_date.year, current_due_date.month

    # บวกเดือนเพิ่ม
    total_months = month + months_to_add
    new_year = year + (total_months - 1) // 12
    new_month = (total_months - 1) % 12 + 1
    
    return datetime(new_year, new_month, 13, 23, 59, 59)