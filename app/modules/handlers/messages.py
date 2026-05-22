import os
import io
import uuid
from datetime import datetime, timedelta
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    FlexSendMessage, ImageSendMessage
)
from app.modules.line_api import line_bot_api, handler
from app.setup.database import (
    users_col, get_user, save_slip_image, register_user, 
    check_is_registered, save_temp_slip_id, find_users_by_nickname, 
    check_nickname_available, create_transaction,
    get_all_registered_users, get_transaction_slip_by_details
)
from app.setup.config import Config
from app.utils.date_time import get_thai_month_year, parse_month_year, calculate_next_due_date_from_text
from app.utils.validators import validate_slip_format
from app.ui.flex_messages import (
    create_admin_flex, create_members_list_text, create_delete_confirm_flex
)

# ============================================================
# TEXT MESSAGE HANDLER
# ============================================================
# All user-facing features are accessed ONLY via Rich Menu.
# Text commands that remain are:
#   - #regis     → Registration (first-time use, no Rich Menu yet)
#   - #โอน       → Part of slip submission flow (step 2, after image)
#   - Admin text commands triggered FROM Rich Menu prompts:
#     #check, #members, #ดูสลิป, #ลบประวัติ, MyID, MyGroup
# ============================================================

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    msg = event.message.text.strip()
    user_id = event.source.user_id
    is_group = event.source.type == "group"

    # --- Admin Commands (gated behind ADMIN_USER_ID) ---
    if msg.startswith("#check") or msg in ["MyID", "MyGroup"] or msg.startswith("#members") or msg.startswith("#ดูสลิป") or msg.startswith("#ลบประวัติ"):
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
                        next_due = u.get('next_due_date')
                        status = get_thai_month_year(next_due) if next_due else "ยังไม่มีข้อมูล"

                        reply_msg += f"- {u.get('first_name')} ({u.get('nickname')}) : บิลถัดไป {status}\n"
                    
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg.strip()))
            except Exception as e:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ คำสั่งผิด! ตัวอย่าง: #check ฝ้าย"))
            return

        if msg.startswith("#members"):
            members = get_all_registered_users()
            reply = create_members_list_text(members)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        if msg.startswith("#ดูสลิป"):
            _process_admin_view_slip(event, msg)
            return

        if msg.startswith("#ลบประวัติ"):
            _process_admin_delete_prompt(event, msg)
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

    # --- Registration (kept as text — first-time user has no Rich Menu yet) ---
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
            
            # Link member Rich Menu after successful registration
            try:
                from app.modules.rich_menu import link_member_menu
                link_member_menu(user_id)
            except Exception as e:
                print(f"Rich Menu link error (non-critical): {e}")
            
            reply = (
                f"✅ ลงทะเบียนสำเร็จ!\n"
                f"ยินดีต้อนรับพี่ {nname} ({email})\n\n"
                f"น้องฝอยพร้อมดูแลค้าบ 🥸☝🏼\n"
                f"กดเมนูด้านล่างเพื่อเริ่มใช้งานได้เลย 👇🏼"
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

    # --- Slip Submission (step 2 of payment flow, triggered after image upload) ---
    if msg.startswith("#โอน"):
        if is_group: return
        if not require_registration(user_id, event.reply_token): return
        
        _process_transfer_submission(event, msg, user_id)


# ============================================================
# IMAGE MESSAGE HANDLER (slip upload — step 1 of payment flow)
# ============================================================

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


# ============================================================
# INTERNAL HELPERS
# ============================================================

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

        current_next_due = user.get('next_due_date')
        
        if current_next_due:
            input_due_date = calculate_next_due_date_from_text(data['billing'], data['months'])
            
            if input_due_date:
                if input_due_date <= current_next_due:
                    last_paid_month = current_next_due - timedelta(days=20) 
                    paid_str = get_thai_month_year(last_paid_month)
                    
                    raise ValueError(
                        f"❌ ยอดนี้จ่ายซ้ำค่ะ!\n\n"
                        f"ข้อมูลล่าสุดพี่จ่ายถึงรอบเดือน **{paid_str}** แล้ว"
                    )
            else:
                raise ValueError("❌ รูปแบบเดือนไม่ถูกต้อง (เช่น 'ม.ค. 68' หรือ 'ม.ค. 68 - มี.ค. 68')")

        # Check Pending Slip
        file_id = user.get('temp_slip_id')
        if not file_id:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ ไม่พบรูปสลิป! ส่งรูปมาก่อนนะคะ"))
            return

        tx_id = str(uuid.uuid4())
        
        # Pass slip_id to transaction for traceability
        create_transaction(
            tx_id, 
            user_id, 
            data['amount'], 
            data['months'], 
            data['billing'],
            slip_id=file_id
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
        
        users_col.update_one(
            {"user_id": user_id}, 
            {"$unset": {"temp_slip_id": "", "slip_uploaded_at": ""}}
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ น้องฝอยบันทึกข้อมูลเรียบร้อยค่ะ! รอแอดมินพี่ฝ้ายตรวจสอบนะคะ ⏳\n\nขอบคุณที่ใช้บริการค้าบ 🤓🫶🏼"))

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"System Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"ระบบขัดข้อง ลองใหม่อีกครั้งนะคะ"))


def _process_admin_view_slip(event, msg):
    """
    Admin views a specific transaction's slip image
    Format: #ดูสลิป [ชื่อเล่น] [เดือน] [ปี]
    Example: #ดูสลิป ฝ้าย ม.ค. 68
    """
    try:
        parts = msg.replace("#ดูสลิป", "").strip()
        if not parts:
            raise ValueError(
                "❌ กรุณาระบุข้อมูลให้ครบ!\n\n"
                "รูปแบบ: #ดูสลิป [ชื่อเล่น] [เดือน] [ปี]\n"
                "ตัวอย่าง: #ดูสลิป ฝ้าย ม.ค. 68"
            )

        tokens = parts.split()
        if len(tokens) < 3:
            raise ValueError(
                "❌ ข้อมูลไม่ครบ!\n\n"
                "รูปแบบ: #ดูสลิป [ชื่อเล่น] [เดือน] [ปี]\n"
                "ตัวอย่าง: #ดูสลิป ฝ้าย ม.ค. 68"
            )

        nickname = tokens[0]
        month_year_text = " ".join(tokens[1:])

        parsed = parse_month_year(month_year_text)
        if not parsed:
            raise ValueError("❌ รูปแบบเดือน/ปีไม่ถูกต้อง!\nตัวอย่าง: ม.ค. 68, ก.พ. 69")

        month, year = parsed

        slip, status = get_transaction_slip_by_details(nickname, month, year)

        if status == "not_found_user":
            raise ValueError(f"❌ ไม่พบสมาชิกชื่อ '{nickname}' ในระบบ")
        elif status == "not_found_tx":
            from app.utils.const import THAI_MONTHS
            month_str = THAI_MONTHS[month - 1]
            thai_year = str((year + 543) % 100)
            raise ValueError(f"❌ ไม่พบรายการของ '{nickname}' ในเดือน {month_str} {thai_year}")
        elif status == "not_found_slip":
            raise ValueError(f"❌ พบรายการแต่ไม่มีรูปสลิปในระบบ")
        elif status == "invalid_month":
            raise ValueError("❌ เดือนที่ระบุไม่ถูกต้อง")

        # Found slip — serve the image
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        slip_id = str(slip["_id"])
        image_url = f"{base_url}/slip/{slip_id}"

        line_bot_api.reply_message(event.reply_token, 
            ImageSendMessage(
                original_content_url=image_url, 
                preview_image_url=image_url
            )
        )

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"Admin View Slip Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ระบบขัดข้อง ลองใหม่อีกครั้งค่ะ"))


def _process_admin_delete_prompt(event, msg):
    """
    Admin deletes transaction history
    Format: #ลบประวัติ [ชื่อเล่น]
    """
    try:
        parts = msg.replace("#ลบประวัติ", "").strip()
        if not parts:
            raise ValueError(
                "❌ กรุณาระบุชื่อเล่นสมาชิก!\n\n"
                "รูปแบบ: #ลบประวัติ [ชื่อเล่น]\n"
                "ตัวอย่าง: #ลบประวัติ ฝ้าย"
            )

        nickname = parts.strip()
        users = find_users_by_nickname(nickname)

        if not users:
            raise ValueError(f"❌ ไม่พบสมาชิกชื่อ '{nickname}' ในระบบ")

        target_user = users[0]
        target_uid = target_user.get("user_id")
        target_nickname = target_user.get("nickname", nickname)

        flex = create_delete_confirm_flex(target_nickname, target_uid)
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="ยืนยันการลบข้อมูล", contents=flex)
        )

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"Admin Delete Prompt Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="ระบบขัดข้อง ลองใหม่อีกครั้งค่ะ"))


def require_registration(user_id, reply_token):
    if not check_is_registered(user_id):
        reply_txt = (
            "⛔️ พี่ ๆ ลงทะเบียนกับน้องฝอยก่อนน้า\n\n"
            "พิมพ์ตามรูปแบบนี้นะคับ:\n"
            "#regis\n"
            "[ชื่อจริง] [นามสกุล]\n"
            "[ชื่อเล่น]\n"
            "[เบอร์]\n"
            "[เมล]"
        )
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_txt))
        return False # Not registered
    return True # Registered