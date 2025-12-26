import os
import uuid
import re
import io
from datetime import datetime
from urllib.parse import quote
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    FlexSendMessage, PostbackEvent, ImageSendMessage, FollowEvent
)
from app.modules.line_api import line_bot_api, handler
from app.database import (
    users_col, get_user, update_user_payment, 
    create_transaction, get_transaction, complete_transaction, reject_transaction,
    save_slip_image, register_user, check_is_registered, save_temp_slip_id,
    find_users_by_nickname, check_nickname_available # ✅ Import ครบ
)
from app.utils import get_thai_time, format_date
from app.config import Config

# --- Constants ---
VALID_BANKS = ["KBank", "SCB", "KTB", "BBL", "TrueWallet", "TTB", "BAY", "GSB"]
MONTH_MAP = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12
}
THAI_MONTHS = list(MONTH_MAP.keys())

# --- Helper Functions ---

def calculate_next_bill_date(start_date, months_to_add):
    """ตัดรอบวันที่ 13 เสมอ"""
    now = datetime.now()
    if not start_date or start_date < now:
        if now.day > 13:
            year, month = now.year, now.month 
        else:
            year, month = now.year, now.month
    else:
        year, month = start_date.year, start_date.month

    total_months = month + months_to_add
    new_year = year + (total_months - 1) // 12
    new_month = (total_months - 1) % 12 + 1
    
    return datetime(new_year, new_month, 13, 23, 59, 59)

def get_thai_month_year(dt):
    if not dt: return "ยังไม่มีข้อมูล"
    return f"{THAI_MONTHS[dt.month-1]} {dt.year+543-2500}"

def get_main_menu_flex():
    text_message = quote("เริ่มจ่ายเงิน")
    payment_url = f"https://line.me/R/oaMessage/{Config.LINE_BOT_BASIC_ID}/?text={text_message}"
    
    return {
        "type": "bubble",
        "hero": {"type": "image", "url": "https://images.unsplash.com/photo-1614680376593-902f74cf0d41?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80", "size": "full", "aspectRatio": "20:13", "aspectMode": "cover"},
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🎵 Spotify Payment Bot", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "น้องฝ้ายมารายงานตัวแล้วค่ะ มีอะไรให้ช่วยมั้ยคะ?", "wrap": True, "color": "#666666", "size": "sm"}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "color": "#1DB954", "action": {"type": "uri", "label": "💸 ชำระเงิน (ส่วนตัว)", "uri": payment_url}},
                {"type": "button", "style": "secondary", "action": {"type": "message", "label": "🔍 เช็คยอดค้าง", "text": "เช็คยอด"}}
            ]
        }
    }

# --- Validator Logic ---

def parse_month_year(text):
    """แกะหา (เดือน, ปี)"""
    found_month = None
    for m_str, m_idx in MONTH_MAP.items():
        if m_str in text:
            found_month = m_idx
            break
    if not found_month: return None

    year_match = re.search(r'\d{2,4}', text)
    if year_match:
        year_val = int(year_match.group())
        if year_val < 100: year_val += 2500
        if year_val < 2400: year_val += 543
    else:
        year_val = datetime.now().year + 543 
    return (found_month, year_val)

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

# --- Event Handlers ---

@handler.add(FollowEvent)
def handle_follow(event):
    reply_txt = (
        "ยินดีต้อนรับสู่ Spotify Bot ค่า 🎉\n\n"
        "📝 **ลงทะเบียนครั้งแรก (เก็บข้อมูลครั้งเดียว)**\n"
        "พิมพ์: `#regis [ชื่อจริง] [นามสกุล] [ชื่อเล่น] [เบอร์โทร] [อีเมล]`\n\n"
        "ตัวอย่าง:\n"
        "#regis สมชาย ใจดี มิก 0812345678 mik@email.com"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    msg = event.message.text.strip()
    user_id = event.source.user_id
    is_group = event.source.type == "group"

    # --- Admin Commands ---
    if msg.startswith("#เช็ค") or msg in ["MyID", "MyGroup"]:
        if user_id != Config.ADMIN_USER_ID: return

        if msg.startswith("#เช็ค"):
            try:
                target_nick = msg.split()[1]
                users = find_users_by_nickname(target_nick)
                if not users:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ ไม่พบ User: {target_nick}"))
                else:
                    reply_msg = f"🔎 ผลการค้นหา ({len(users)} คน):\n"
                    for u in users:
                        status = get_thai_month_year(u.get('paid_until'))
                        reply_msg += f"- {u.get('first_name')} ({u.get('nickname')}) : หมดอายุ {status}\n"
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ พิมพ์ผิด! ตัวอย่าง: #เช็ค มิก"))
            return

        if msg == "MyID":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"User ID: {user_id}"))
            return
        if msg == "MyGroup":
            if is_group:
                group_id = event.source.group_id
                line_bot_api.push_message(user_id, TextSendMessage(text=f"🔑 Group ID: {group_id}"))
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ส่ง ID เข้าแชทส่วนตัวแล้วค่ะ"))
            return

    # --- Registration (New Format + Unique Nickname) ---
    if msg.startswith("#regis"):
        try:
            parts = msg.split()
            if len(parts) != 6:
                raise ValueError("ข้อมูลไม่ครบ! ต้องมี: ชื่อ นามสกุล ชื่อเล่น เบอร์ อีเมล")
            
            fname, lname, nname, tel, email = parts[1], parts[2], parts[3], parts[4], parts[5]
            
            # 🔥 Check Unique Nickname
            if not check_nickname_available(nname, user_id):
                raise ValueError(f"❌ ชื่อเล่น '{nname}' มีคนใช้แล้วค่ะ!\n(กรุณาใช้ชื่ออื่น หรือเติมเลขต่อท้าย)")

            register_user(user_id, fname, lname, nname, tel, email)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"✅ ลงทะเบียนสำเร็จ!\nยินดีต้อนรับคุณ {nname} ({email})\nเริ่มใช้งานเมนูได้เลย 👇"))
        except ValueError as e:
             line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ {str(e)}\n\nตัวอย่าง:\n#regis สมชาย ใจดี มิก 0812345678 mik@mail.com"))
        return

    # --- Gatekeeper ---
    if not check_is_registered(user_id):
        reply_txt = "⛔️ **กรุณาลงทะเบียนก่อนค่ะ**\nพิมพ์: `#regis [ชื่อ] [นามสกุล] [ชื่อเล่น] [เบอร์] [เมล]`"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))
        return

    # --- User Commands ---
    if msg == "ฝ้ายมานี่หน่อยยย":
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="เมนูหลัก", contents=get_main_menu_flex()))
        return

    if msg == "เริ่มจ่ายเงิน":
        if is_group:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="กดปุ่มในเมนูเพื่อทำรายการในแชทส่วนตัวนะคะ 🔒"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="เข้าสู่โหมดชำระเงินค่ะ 🔒\n1. ส่ง **รูปสลิป** มาก่อนได้เลย\n2. แล้วค่อยพิมพ์แจ้งรายละเอียดตาม format"))
        return

    if msg == "เช็คยอด":
        user_data = get_user(user_id)
        if not user_data or not user_data.get('paid_until'):
             reply = "คุณยังไม่มีประวัติการชำระเงินค่ะ เริ่มจ่ายรอบแรกก่อนน้า"
        else:
            paid_until = user_data.get('paid_until')
            now = datetime.now()
            month_str = get_thai_month_year(paid_until)
            if paid_until > now:
                reply = f"✅ สถานะ: ปกติ\n(ชำระถึงรอบ: {month_str})"
            else:
                reply = f"❌ ค้างชำระ!\n(คุณชำระล่าสุดถึงรอบ: {month_str})\nตอนนี้มียอดค้างชำระค่ะ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if msg.startswith("#โอน"):
        if is_group: return
        process_transfer_submission(event, msg, user_id)

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    if event.source.type == "group": return
    user_id = event.source.user_id

    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ กรุณาลงทะเบียนก่อนส่งสลิปนะคะ\nพิมพ์: #regis ..."))
        return

    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        file_stream = io.BytesIO()
        for chunk in message_content.iter_content():
            file_stream.write(chunk)
        file_stream.seek(0)
        
        file_id = save_slip_image(file_stream, f"{event.message.id}.jpg")
        save_temp_slip_id(user_id, file_id)

        bank_list_str = ", ".join(VALID_BANKS)
        reply_txt = (
            "ได้รับสลิปแล้วค่ะ 📥\n\n"
            "พิมพ์รายละเอียดตามนี้นะคะ:\n"
            "#โอน [ชื่อเล่น] [จำนวนเงิน] [จำนวนเดือน] [ช่วงเดือน] [ธนาคาร] [วัน เดือน ปี] [เวลา]\n\n"
            f"🏦 **ธนาคาร:** {bank_list_str}\n"
            "⚠️ ชื่อเล่นต้องตรงกับที่ลงทะเบียนไว้นะคะ"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))

    except Exception as e:
        print(f"Error saving image: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="เกิดข้อผิดพลาดในการบันทึกรูป ลองใหม่อีกครั้งนะคะ"))

# --- Process Logic ---

def process_transfer_submission(event, msg, user_id):
    try:
        data = validate_slip_format(msg)
        user = get_user(user_id)
        if not user:
             line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ไม่พบข้อมูล (DB Error)"))
             return

        # Check Name (Privacy Safe)
        registered_nickname = user.get('nickname', '')
        if data['nickname'].strip().lower() != registered_nickname.strip().lower():
            raise ValueError(f"❌ ชื่อเล่นไม่ถูกต้อง (ไม่ตรงกับที่ลงทะเบียนไว้)")

        # 🔥 Check Overlap (Double Payment)
        current_paid = user.get('paid_until')
        if current_paid:
            billing_start_str = data['billing'].split('-')[0].split('ถึง')[0].strip()
            parsed_start = parse_month_year(billing_start_str)
            
            if parsed_start:
                input_m, input_y = parsed_start
                paid_m = current_paid.month
                paid_y = current_paid.year
                
                input_code = input_y * 100 + input_m
                paid_code = paid_y * 100 + paid_m
                
                if input_code <= paid_code:
                    paid_str = get_thai_month_year(current_paid)
                    raise ValueError(f"❌ ยอดนี้จ่ายซ้ำค่ะ!\nคุณจ่ายถึงเดือน **{paid_str}** แล้ว\n(เดือน {billing_start_str} อยู่ในระยะที่ครอบคลุมแล้ว)")

        # Check Pending Slip
        file_id = user.get('temp_slip_id')
        if not file_id:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ ไม่พบรูปสลิป! ส่งรูปมาก่อนนะคะ"))
            return

        tx_id = str(uuid.uuid4())
        
        # Create Tx (Lean Schema)
        create_transaction(
            tx_id, user_id, 
            data['amount'], data['months'], data['billing'],
            data['bank'], data['datetime']
        )

        # Notify Admin (With Tel/Email)
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        image_url = f"{base_url}/slip/{file_id}"
        
        flex_msg = create_admin_flex(
            data['nickname'], data['amount'], data['months'], 
            data['bank'], data['datetime'], data['billing'], tx_id
        )
        
        full_info = f"{user.get('first_name')} {user.get('last_name')}\n📞 {user.get('tel_number', '-')}\n📧 {user.get('email', '-')}"
        
        line_bot_api.push_message(Config.ADMIN_USER_ID, [
            TextSendMessage(text=f"📨 แจ้งโอนจาก {data['nickname']}\n{full_info}"),
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url),
            FlexSendMessage(alt_text="บิลแจ้งโอน", contents=flex_msg)
        ])
        
        users_col.update_one({"user_id": user_id}, {"$unset": {"temp_slip_id": ""}})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ บันทึกข้อมูลเรียบร้อยค่ะ! รอแอดมินตรวจสอบนะคะ ⏳"))

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"System Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"ระบบขัดข้อง: {e}"))

def create_admin_flex(name, amount, months, bank, time, bill_month, tx_id):
    display_amount = f"{amount:g}"
    return {
        "type": "bubble",
        "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "📝 รายการโอนเงินใหม่", "weight": "bold", "color": "#1DB954"}]},
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"User: {name}", "size": "lg", "weight": "bold"},
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": f"💰 ยอดโอน: {display_amount} บาท"},
                {"type": "text", "text": f"📅 จำนวน: {months} เดือน"},
                {"type": "text", "text": f"🧾 บิลของ: {bill_month}", "color": "#0000ff", "weight": "bold"},
                {"type": "text", "text": f"🏦 ธนาคาร: {bank}"},
                {"type": "text", "text": f"⏰ เวลาโอน: {time}"}
            ]
        },
        "footer": {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "action": {"type": "postback", "label": "รับยอด", "data": f"action=approve&txid={tx_id}"}},
                {"type": "button", "style": "secondary", "action": {"type": "postback", "label": "ยกเลิก", "data": f"action=reject&txid={tx_id}"}}
            ]
        }
    }

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    params = dict(x.split('=') for x in data.split('&'))
    action = params.get('action')
    tx_id = params.get('txid')
    admin_id = event.source.user_id

    transaction = get_transaction(tx_id)
    if not transaction:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ไม่พบข้อมูลรายการนี้"))
        return

    if transaction['status'] != 'pending':
        status_msg = "อนุมัติ" if transaction['status'] == 'completed' else "ปฏิเสธ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"⚠️ รายการนี้ถูก '{status_msg}' ไปแล้วค่ะ"))
        return

    if action == 'approve':
        process_approve(event, transaction, tx_id, admin_id)
    elif action == 'reject':
        reject_transaction(tx_id)
        line_bot_api.push_message(transaction['uid'], TextSendMessage(text="❌ ยอดโอนถูกปฏิเสธ (ข้อมูลไม่ถูกต้อง) ทักแชทแอดมินได้เลยค่ะ"))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="กดปฏิเสธเรียบร้อย"))

def process_approve(event, tx_data, tx_id, admin_id):
    user_id = tx_data['uid']
    months = int(tx_data['cnt_month'])

    user_record = get_user(user_id)
    current_paid = user_record.get('paid_until') if user_record else None
    
    new_paid = calculate_next_bill_date(current_paid, months)
    
    update_user_payment(user_id, tx_id, new_paid)
    complete_transaction(tx_id)

    thai_date_str = f"13 {THAI_MONTHS[new_paid.month-1]} {new_paid.year+543-2500}"
    line_bot_api.push_message(user_id, TextSendMessage(text=f"✅ แอดมินรับยอดแล้ว!\nรอบบิลของคุณอัปเดตถึงวันที่: {thai_date_str}"))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บันทึกยอดเรียบร้อย (หมดอายุ {thai_date_str})"))