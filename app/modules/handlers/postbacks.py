from linebot.models import PostbackEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler
from app.setup.database import (
    get_transaction, get_user, update_user_payment, 
    complete_transaction, reject_transaction
)
from app.utils.date_time import calculate_next_bill_date, THAI_MONTHS

@handler.add(PostbackEvent)
def handle_postback(event):
    data = event.postback.data
    params = dict(x.split('=') for x in data.split('&'))
    action = params.get('action')
    tx_id = params.get('txid')

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

def _process_approve(event, tx_data, tx_id):
    user_id = tx_data['uid']
    months = int(tx_data['cnt_month'])

    user_record = get_user(user_id)
    current_paid = user_record.get('paid_until') if user_record else None
    
    new_paid = calculate_next_bill_date(current_paid, months)
    
    update_user_payment(user_id, tx_id, new_paid)
    complete_transaction(tx_id)

    thai_date_str = f"13 {THAI_MONTHS[new_paid.month-1]} {new_paid.year+543-2500}"
    line_bot_api.push_message(user_id, TextSendMessage(text=f"✅ แอดมินพี่ฝ้ายรับยอดแล้ว!\nรอบบิลถัดไป: {thai_date_str}"))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"บันทึกยอดเรียบร้อย (บิลรอบถัดไป: {thai_date_str})"))