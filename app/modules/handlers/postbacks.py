from linebot.models import PostbackEvent, TextSendMessage, FlexSendMessage
from app.modules.line_api import line_bot_api, handler
from app.setup.database import (
    get_transaction, get_user, update_user_payment, 
    complete_transaction, reject_transaction,
    get_user_transactions, get_all_member_statuses,
    soft_delete_transactions, hard_delete_transactions,
    check_is_registered
)
from app.setup.config import Config
from app.utils.date_time import calculate_next_due_date_from_text, THAI_MONTHS
from app.ui.flex_messages import (
    create_user_transactions_text, create_admin_status_text,
    create_delete_confirm_flex
)

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    params = dict(x.split('=') for x in data.split('&'))
    action = params.get('action')
    user_id = event.source.user_id

    # --- Member Postback Actions ---
    if action == 'my_transactions':
        _handle_my_transactions(event, user_id)
        return

    if action == 'start_payment':
        _handle_start_payment(event, user_id)
        return

    if action == 'member_help':
        _handle_member_help(event, user_id)
        return

    # --- Admin Postback Actions ---
    if action == 'admin_all_status':
        _handle_admin_all_status(event, user_id)
        return

    if action == 'admin_delete_menu':
        _handle_admin_delete_menu(event, user_id)
        return

    if action == 'admin_view_slip_prompt':
        _handle_admin_view_slip_prompt(event, user_id)
        return

    if action == 'admin_help':
        _handle_admin_help(event, user_id)
        return

    if action == 'confirm_soft_delete':
        _handle_confirm_soft_delete(event, user_id, params)
        return

    if action == 'confirm_hard_delete':
        _handle_confirm_hard_delete(event, user_id, params)
        return

    if action == 'cancel_delete':
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ ยกเลิกการลบข้อมูลแล้วค่ะ"))
        return

    # --- Existing Transaction Approve/Reject ---
    tx_id = params.get('txid')
    if not tx_id:
        return

    transaction = get_transaction(tx_id)
    if not transaction:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ไม่พบข้อมูลรายการนี้"))
        return

    if transaction['status'] != 'pending':
        status_msg = "อนุมัติ" if transaction['status'] == 'completed' else "ปฏิเสธ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"⚠️ รายการนี้ถูก '{status_msg}' ไปแล้วค่ะ"))
        return

    if action == 'approve':
        _process_approve(event, transaction, tx_id)
    elif action == 'reject':
        reject_transaction(tx_id)
        line_bot_api.push_message(transaction['uid'], TextSendMessage(text="❌ ยอดโอนถูกปฏิเสธ (ข้อมูลไม่ถูกต้อง) ทักแชทหาแอดมินพี่ฝ้ายได้เลยค่ะ!"))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="กดปฏิเสธเรียบร้อย"))


# ============================================================
# MEMBER POSTBACK HANDLERS
# ============================================================

def _handle_my_transactions(event, user_id):
    """Member views their own transactions (paid vs pending) + due date status"""
    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ กรุณาลงทะเบียนก่อนนะคะ"))
        return

    user = get_user(user_id)
    nickname = user.get('nickname', 'ไม่ทราบ')
    transactions = get_user_transactions(user_id)

    reply_parts = []

    # Transaction list
    tx_text = create_user_transactions_text(transactions, nickname)
    reply_parts.append(tx_text)

    # Add next due date status
    next_due = user.get('next_due_date')
    if next_due:
        from datetime import datetime
        from app.utils.date_time import get_thai_month_year
        now = datetime.now()
        month_str = get_thai_month_year(next_due)

        if next_due > now:
            reply_parts.append(f"\n📅 รอบบิลถัดไป: 13 {month_str}")
            reply_parts.append("🟢 สถานะ: ปกติ")
        else:
            reply_parts.append(f"\n📅 ครบกำหนดรอบ: 13 {month_str}")
            reply_parts.append("🔴 สถานะ: เลยกำหนดชำระ!")
    else:
        reply_parts.append("\n📅 ยังไม่มีกำหนดชำระรอบถัดไป")

    reply = "\n".join(reply_parts)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_start_payment(event, user_id):
    """Member initiates payment flow via Rich Menu (replaces old text trigger)"""
    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ กรุณาลงทะเบียนก่อนนะคะ\nพิมพ์: #regis ..."))
        return

    reply = (
        "เข้าสู่โหมดชำระเงินคับ 🧾\n"
        "1. ส่ง \"รูปสลิป\" มาก่อนได้เลย\n"
        "2. แล้วค่อยพิมพ์แจ้งรายละเอียดในขั้นตอนถัดไป!"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_member_help(event, user_id):
    """Req 4.1: Member views all available commands"""
    reply = (
        "❓ คำสั่งทั้งหมดสำหรับสมาชิก\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 เมนูด้านล่าง (Rich Menu):\n"
        "• 📋 ดูรายการ — ดูประวัติชำระเงิน\n"
        "  (จ่ายแล้ว / รอตรวจสอบ / สถานะบิล)\n"
        "• 💸 ส่งสลิป — เริ่มส่งสลิปชำระเงิน\n"
        "  (ส่งรูปสลิป → พิมพ์ #โอน)\n"
        "• ❓ คำสั่ง — ดูหน้านี้\n\n"
        "🔹 พิมพ์ข้อความ:\n"
        "• #regis — ลงทะเบียนสมาชิกใหม่\n"
        "  (ชื่อ-สกุล, ชื่อเล่น, เบอร์, อีเมล)\n"
        "• #โอน — แจ้งรายละเอียดการโอนเงิน\n"
        "  (ใช้หลังจากส่งรูปสลิปแล้ว)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 ขั้นตอนการชำระเงิน:\n"
        "1️⃣ กด 💸 ส่งสลิป ในเมนู\n"
        "2️⃣ ส่งรูปสลิปการโอน\n"
        "3️⃣ พิมพ์ #โอน พร้อมรายละเอียด\n"
        "4️⃣ รอแอดมินตรวจสอบ ✅"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


# ============================================================
# ADMIN POSTBACK HANDLERS
# ============================================================

def _handle_admin_all_status(event, user_id):
    """Admin views all member statuses"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    statuses = get_all_member_statuses()
    reply = create_admin_status_text(statuses)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_admin_delete_menu(event, user_id):
    """Admin initiates delete flow"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    reply = (
        "🗑️ ลบประวัติรายการ\n\n"
        "พิมพ์คำสั่งตามนี้:\n"
        "#ลบประวัติ [ชื่อเล่น]\n\n"
        "ตัวอย่าง:\n"
        "#ลบประวัติ ฝ้าย"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_admin_view_slip_prompt(event, user_id):
    """Admin initiates slip view flow"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    reply = (
        "🖼️ ดูสลิปรายการ\n\n"
        "พิมพ์คำสั่งตามนี้:\n"
        "#ดูสลิป [ชื่อเล่น] [เดือน] [ปี]\n\n"
        "ตัวอย่าง:\n"
        "#ดูสลิป ฝ้าย ม.ค. 68"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_admin_help(event, user_id):
    """Req 5.1: Admin views all available commands"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    reply = (
        "❓ คำสั่งทั้งหมดสำหรับแอดมิน\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔹 เมนูด้านล่าง (Rich Menu):\n"
        "• 📊 สถานะสมาชิก — ดูสถานะทุกคน\n"
        "  (จ่ายล่าสุดวันไหน / ค้างชำระไหม)\n"
        "• 🗑️ ลบประวัติ — ลบประวัติรายการ\n"
        "  (Soft Delete / Hard Delete)\n"
        "• 🖼️ ดูสลิป — ดูรูปสลิปรายการเฉพาะ\n"
        "• ❓ คำสั่ง — ดูหน้านี้\n\n"
        "🔹 พิมพ์ข้อความ:\n"
        "• #members — ดูรายชื่อสมาชิกทั้งหมด\n"
        "• #check [ชื่อเล่น] — ตรวจสอบสมาชิกเฉพาะคน\n"
        "  ตัวอย่าง: #check ฝ้าย\n"
        "• #ดูสลิป [ชื่อ] [เดือน] [ปี] — ดูรูปสลิป\n"
        "  ตัวอย่าง: #ดูสลิป ฝ้าย ม.ค. 68\n"
        "• #ลบประวัติ [ชื่อเล่น] — ลบประวัติรายการ\n"
        "  ตัวอย่าง: #ลบประวัติ ฝ้าย\n"
        "• MyID — ดู User ID ของตัวเอง\n"
        "• MyGroup — ดู Group ID (ใช้ในกลุ่ม)"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_confirm_soft_delete(event, user_id, params):
    """Soft delete (mark as deleted)"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    target_uid = params.get('target_uid')
    if not target_uid:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ข้อมูลไม่ครบ"))
        return

    target_user = get_user(target_uid)
    target_name = target_user.get('nickname', 'ไม่ทราบ') if target_user else 'ไม่ทราบ'

    count = soft_delete_transactions(target_uid)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"✅ Soft Delete สำเร็จ!\n\nซ่อนประวัติของ '{target_name}' จำนวน {count} รายการ\n(ข้อมูลยังอยู่ในระบบ สามารถกู้คืนได้)")
    )


def _handle_confirm_hard_delete(event, user_id, params):
    """Hard delete (permanent removal from MongoDB)"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⛔️ คำสั่งนี้สำหรับแอดมินเท่านั้น"))
        return

    target_uid = params.get('target_uid')
    if not target_uid:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ ข้อมูลไม่ครบ"))
        return

    target_user = get_user(target_uid)
    target_name = target_user.get('nickname', 'ไม่ทราบ') if target_user else 'ไม่ทราบ'

    count = hard_delete_transactions(target_uid)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"🗑️ Hard Delete สำเร็จ!\n\nลบประวัติของ '{target_name}' จำนวน {count} รายการถาวร\n⚠️ ไม่สามารถกู้คืนได้")
    )


# ============================================================
# EXISTING APPROVE HANDLER
# ============================================================

def _process_approve(event, tx_data, tx_id):
    user_id = tx_data['uid']
    months = int(tx_data['cnt_month'])
    billing_txt = tx_data['billing'] 

    new_due_date = calculate_next_due_date_from_text(billing_txt, months)
    
    if not new_due_date:
        from app.utils.date_time import calculate_next_bill_date
        user_record = get_user(user_id)
        current_due = user_record.get('next_due_date') if user_record else None
        new_due_date = calculate_next_bill_date(current_due, months)

    update_user_payment(user_id, tx_id, new_due_date)
    complete_transaction(tx_id)

    thai_year = new_due_date.year + 543
    thai_month = THAI_MONTHS[new_due_date.month-1]
    thai_date_str = f"13 {thai_month} {str(thai_year)[2:]}" 

    line_bot_api.push_message(user_id, TextSendMessage(text=f"✅ แอดมินพี่ฝ้ายรับยอดแล้ว!\n(รอบบิลถัดไป: {thai_date_str})"))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บันทึกยอดเรียบร้อย (รอบบิลถัดไป: {thai_date_str})"))