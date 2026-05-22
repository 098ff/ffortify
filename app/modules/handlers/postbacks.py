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
    create_user_transactions_text, create_admin_status_text
)
from app.messages.no_param import (
    CANCEL_DELETE, NOT_FOUND_TRANSACTION, REGISTRATION_PROMPT,
    REGISTRATION_PROMPT_WITH_FORMAT, MEMBER_HELP, START_PAYMENT,
    ADMIN_ONLY, ADMIN_DELETE_MENU_PROMPT, ADMIN_VIEW_SLIP_PROMPT,
    ADMIN_HELP, ADMIN_CONFIRM_DELETE_MISSING_DATA, REJECT_REPLY,
    REJECT_PUSH_MSG, UNREGISTERED_WELCOME, UNREGISTERED_HELP
)
from app.messages.with_param import (
    admin_already_processed, admin_push_approved, admin_reply_approved,
    admin_soft_delete_success, admin_hard_delete_success
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

    # --- Unregistered Postback Actions ---
    if action == 'start_registration':
        _handle_start_registration(event, user_id)
        return

    if action == 'default_help':
        _handle_default_help(event, user_id)
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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=CANCEL_DELETE))
        return

    # --- Existing Transaction Approve/Reject ---
    tx_id = params.get('txid')
    if not tx_id:
        return

    transaction = get_transaction(tx_id)
    if not transaction:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=NOT_FOUND_TRANSACTION))
        return

    if transaction['status'] != 'pending':
        status_msg = "อนุมัติ" if transaction['status'] == 'completed' else "ปฏิเสธ"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=admin_already_processed(status_msg)))
        return

    if action == 'approve':
        _process_approve(event, transaction, tx_id)
    elif action == 'reject':
        reject_transaction(tx_id)
        line_bot_api.push_message(transaction['uid'], TextSendMessage(text=REJECT_PUSH_MSG))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=REJECT_REPLY))


# ============================================================
# MEMBER POSTBACK HANDLERS
# ============================================================

def _handle_my_transactions(event, user_id):
    """Member views their own transactions (paid vs pending) + due date status"""
    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=REGISTRATION_PROMPT))
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
    """Member initiates payment flow via Rich Menu"""
    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=REGISTRATION_PROMPT_WITH_FORMAT))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=START_PAYMENT))


def _handle_member_help(event, user_id):
    """Req 4.1: Member views all available commands"""
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=MEMBER_HELP))


# ============================================================
# ADMIN POSTBACK HANDLERS
# ============================================================

def _handle_admin_all_status(event, user_id):
    """Admin views all member statuses"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    statuses = get_all_member_statuses()
    reply = create_admin_status_text(statuses)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def _handle_admin_delete_menu(event, user_id):
    """Admin initiates delete flow"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_DELETE_MENU_PROMPT))


def _handle_admin_view_slip_prompt(event, user_id):
    """Admin initiates slip view flow"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_VIEW_SLIP_PROMPT))


def _handle_admin_help(event, user_id):
    """Req 5.1: Admin views all available commands"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_HELP))


def _handle_confirm_soft_delete(event, user_id, params):
    """Soft delete (mark as deleted)"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    target_uid = params.get('target_uid')
    if not target_uid:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_CONFIRM_DELETE_MISSING_DATA))
        return

    target_user = get_user(target_uid)
    target_name = target_user.get('nickname', 'ไม่ทราบ') if target_user else 'ไม่ทราบ'

    count = soft_delete_transactions(target_uid)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=admin_soft_delete_success(target_name, count))
    )


def _handle_confirm_hard_delete(event, user_id, params):
    """Hard delete (permanent removal from MongoDB)"""
    if user_id != Config.ADMIN_USER_ID:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_ONLY))
        return

    target_uid = params.get('target_uid')
    if not target_uid:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_CONFIRM_DELETE_MISSING_DATA))
        return

    target_user = get_user(target_uid)
    target_name = target_user.get('nickname', 'ไม่ทราบ') if target_user else 'ไม่ทราบ'

    count = hard_delete_transactions(target_uid)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=admin_hard_delete_success(target_name, count))
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

    line_bot_api.push_message(user_id, TextSendMessage(text=admin_push_approved(thai_date_str)))
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=admin_reply_approved(thai_date_str)))


def _handle_start_registration(event, user_id):
    """Sends the registration instruction text to unregistered users"""
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=UNREGISTERED_WELCOME))


def _handle_default_help(event, user_id):
    """Provides information on how to register and start using the bot"""
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=UNREGISTERED_HELP))