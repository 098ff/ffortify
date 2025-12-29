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
    if msg.startswith("#check") or msg in ["MyID", "MyGroup"]:
        if user_id != Config.ADMIN_USER_ID: return

        if msg.startswith("#check"):
            try:
                target_nick = msg.split()[1]
                users = find_users_by_nickname(target_nick)
                if not users:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ ไม่พบบัญชีผู้ใช้งานนี้: {target_nick}"))
                else:
                    reply_msg = f"🔎 ผลการค้นหา:\n\n"
                    for u in users:
                        status = get_thai_month_year(u.get('paid_until'))
                        reply_msg += f"- {u.get('first_name')} ({u.get('nickname')}) : ยอดชำระล่าสุด {status}\n"
                    reply_msg.strip('\n')
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg))
            except:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ คำสั่งผิด! ตัวอย่าง: #check ฝ้าย"))
            return

        if msg == "MyID":
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"User ID: {user_id}"))
            return
        if msg == "MyGroup":
            if is_group:
                group_id = event.source.group_id
                line_bot_api.push_message(user_id, TextSendMessage(text=f"Group ID: {group_id}"))
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ส่ง ID ไปที่แชทส่วนตัวฝ้ายนะ!"))
            return

    # --- Registration ---
    if msg.startswith("#regis"):
        try:
            lines = [line.strip() for line in msg.split('\n') if line.strip()]
            
            if len(lines) < 5:
                raise ValueError("ข้อมูลไม่ครบ! พี่ ๆ สามารถดูตัวอย่างการพิมพ์ตามข้างล่างได้เลย 👇🏼")
        
            full_name = lines[1].split() 
            if len(full_name) < 2:
                raise ValueError("ฝากพี่ ๆ พิมพ์ 'ชื่อ' และ 'นามสกุล' ให้ครบด้วยน้า (มีเว้นวรรค)")
            
            fname = full_name[0]
            lname = " ".join(full_name[1:])
            
            nname = lines[2]
            tel = lines[3]
            email = lines[4]
            
            if not check_nickname_available(nname, user_id):
                raise ValueError(f"❌ ชื่อเล่น '{nname}' มีคนใช้แล้วค่ะ!")

            register_user(user_id, fname, lname, nname, tel, email)
            
            # ปรับข้อความตอบกลับให้น่ารัก
            reply = (
                f"✅ ลงทะเบียนสำเร็จ!\n"
                f"ยินดีต้อนรับพี่ {nname} ({email})\n\n"
                f"น้องฝอยพร้อมดูแลค้าบ 🥸☝🏼"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

        except ValueError as e:
            err_msg = (
                f"❌ {str(e)}\n\n"
                "ตัวอย่างการพิมพ์:\n"
                "#regis\n"
                "ชนัดดา คนชม\n"
                "ฝ้าย\n"
                "0812345678\n"
                "fforfaii@gmail.com"
            )
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=err_msg))
        return

    # --- Gatekeeper ---
    if not check_is_registered(user_id):
        reply_txt = "⛔️ พี่ ๆ ลงทะเบียนกับน้องฝอยก่อนน้า\n\nรูปแบบการพิมพ์:\n#regis\n[ชื่อจริง] [นามสกุล]\n[ชื่อเล่น]\n[เบอร์]\n[เมล]"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))
        return

    # --- User Commands ---
    if msg.startswith("น้องฝอย"):
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(alt_text="เมนูหลัก", contents=get_main_menu_flex()))
        return

    if ("จ่ายเงิน" in msg) or ("ชำระเงิน" in msg):
        if is_group:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="พี่ ๆ สามารถเรียก \"น้องฝอย\" เพื่อกดปุ่มในเมนูทำรายการในแชทส่วนตัวนะคะ 🔒"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="เข้าสู่โหมดชำระเงินคับ 🧾\n1. ส่ง \"รูปสลิป\" มาก่อนได้เลย\n2. แล้วค่อยพิมพ์แจ้งรายละเอียดในขั้นตอนถัดไป!"))
        return

    if "เช็คยอด" in msg:
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
                reply = f"❌ ค้างชำระ!\n(ชำระล่าสุดถึงรอบ: {month_str})\nตอนนี้มียอดค้างชำระค่ะ"
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

        reply_txt = (
            "ได้รับสลิปแล้วค่ะ 📥\n\n"
            "พิมพ์รายละเอียด **แยกบรรทัด** ตามนี้นะคะ:\n\n"
            "#โอน\n"
            "[ชื่อเล่น]\n"
            "[จำนวนเงิน]\n"
            "[จำนวนเดือน]\n"
            "[ช่วงเดือน]\n\n"
            "ตัวอย่าง:\n"
            "#โอน\n"
            "ฝอฝ้าย\n"
            "41.50\n"
            "2\n"
            "ธ.ค. 68 - ม.ค. 69"
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
             line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ไม่พบข้อมูล"))
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
                    raise ValueError(f"❌ ยอดนี้จ่ายซ้ำค่ะ!\nพี่จ่ายถึงเดือน **{paid_str}** แล้ว\n(เดือน {billing_start_str} อยู่ในระยะที่ครอบคลุมแล้ว)")

        # Check Pending Slip
        file_id = user.get('temp_slip_id')
        if not file_id:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ ไม่พบรูปสลิป! ส่งรูปมาก่อนนะคะ"))
            return

        tx_id = str(uuid.uuid4())
        
        create_transaction(
            tx_id, 
            user_id, 
            data['amount'], 
            data['months'], 
            data['billing']
        )

        # Notify Admin
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        file_id = user.get('temp_slip_id')
        image_url = f"{base_url}/slip/{file_id}"
        
        flex_msg = create_admin_flex(
            data['nickname'], 
            data['amount'], 
            data['months'], 
            data['billing'], 
            tx_id
        )
        
        full_info = f"{user.get('first_name')} {user.get('last_name')}\n📞 {user.get('tel_number', '-')}\n📧 {user.get('email', '-')}"
        
        line_bot_api.push_message(Config.ADMIN_USER_ID, [
            TextSendMessage(text=f"📨 แจ้งโอนจาก {data['nickname']}\n{full_info}"),
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url),
            FlexSendMessage(alt_text="บิลแจ้งโอน", contents=flex_msg)
        ])
        
        users_col.update_one({"user_id": user_id}, {"$unset": {"temp_slip_id": ""}})
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ น้องฝอยบันทึกข้อมูลเรียบร้อยค่ะ! รอแอดมินพี่ฝ้ายตรวจสอบนะคะ ⏳\n\nขอบคุณที่ใช้บริการค้าบ 🤓🫶🏼"))

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"System Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"ระบบขัดข้อง ลองใหม่อีกครั้งนะคะ"))