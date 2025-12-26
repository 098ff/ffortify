import os
import io
import uuid
from datetime import datetime

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    FlexSendMessage, ImageSendMessage
)
from app.modules.line_api import line_bot_api, handler
from app.setup.database import (
    users_col, get_user, save_slip_image, register_user, 
    check_is_registered, save_temp_slip_id, find_users_by_nickname, 
    check_nickname_available, create_transaction
)
from app.setup.config import Config
from app.utils.const import VALID_BANKS
from app.utils.date_time import get_thai_month_year, parse_month_year
from app.utils.validators import validate_slip_format
from app.ui.flex_messages import get_main_menu_flex, create_admin_flex

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

    # --- Registration ---
    if msg.startswith("#regis"):
        try:
            parts = msg.split()
            if len(parts) != 6:
                raise ValueError("ข้อมูลไม่ครบ! ต้องมี: ชื่อ นามสกุล ชื่อเล่น เบอร์ อีเมล")
            
            fname, lname, nname, tel, email = parts[1], parts[2], parts[3], parts[4], parts[5]
            
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
        _process_transfer_submission(event, msg, user_id)

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

# --- Internal Helper ---
def _process_transfer_submission(event, msg, user_id):
    try:
        data = validate_slip_format(msg)
        user = get_user(user_id)
        if not user:
             line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ไม่พบข้อมูล (DB Error)"))
             return

        # Check Name
        registered_nickname = user.get('nickname', '')
        if data['nickname'].strip().lower() != registered_nickname.strip().lower():
            raise ValueError(f"❌ ชื่อเล่นไม่ถูกต้อง (ไม่ตรงกับที่ลงทะเบียนไว้)")

        # Check Overlap
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
        
        create_transaction(
            tx_id, user_id, 
            data['amount'], data['months'], data['billing'],
            data['bank'], data['datetime']
        )

        # Notify Admin
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