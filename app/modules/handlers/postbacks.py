from linebot.models import PostbackEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler
from app.setup.database import (
    get_transaction, get_user, update_user_payment, 
    complete_transaction, reject_transaction
)
from app.utils.date_time import calculate_next_due_date_from_text, THAI_MONTHS

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