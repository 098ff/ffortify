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
from app.messages.no_param import (
    REGISTRATION_PROMPT_WITH_FORMAT, ADMIN_GROUP_ID_REPLY,
    REGISTRATION_ERROR_MISSING_DATA, REGISTRATION_ERROR_NAME_INCOMPLETE,
    SLIP_SUBMISSION_FLOW_STEP2, SLIP_SAVE_ERROR, USER_NOT_FOUND,
    SLIP_SUBMISSION_NICKNAME_MISMATCH, SLIP_SUBMISSION_INVALID_DATE,
    SLIP_SUBMISSION_MISSING_IMAGE, SLIP_SUBMISSION_SUCCESS,
    SLIP_SUBMISSION_SYSTEM_ERROR, ADMIN_VIEW_SLIP_USAGE_ERROR,
    ADMIN_VIEW_SLIP_FORMAT_ERROR, ADMIN_VIEW_SLIP_INVALID_MONTH,
    ADMIN_VIEW_SLIP_NO_SLIP, ADMIN_VIEW_SLIP_SYSTEM_ERROR,
    ADMIN_DELETE_USAGE_ERROR, ADMIN_DELETE_SYSTEM_ERROR,
    ADMIN_CHECK_USAGE_ERROR, REQUIRE_REGISTRATION_PROMPT
)
from app.messages.with_param import (
    admin_check_not_found, admin_check_item, admin_my_id,
    admin_my_group, registration_nickname_taken, registration_success,
    registration_error_prompt, slip_submission_duplicate,
    admin_view_slip_not_found_user, admin_view_slip_not_found_tx,
    admin_delete_not_found_user, admin_notify_transfer_header
)

# ============================================================
# TEXT MESSAGE HANDLER
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
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=admin_check_not_found(target_nick)))
                else:
                    reply_msg = f"🔎 ผลการค้นหา:\n\n"
                    for u in users:
                        next_due = u.get('next_due_date')
                        status = get_thai_month_year(next_due) if next_due else "ยังไม่มีข้อมูล"
                        reply_msg += admin_check_item(u.get('first_name'), u.get('nickname'), status)
                    
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_msg.strip()))
            except Exception as e:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_CHECK_USAGE_ERROR))
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
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=admin_my_id(user_id)))
            return
        if msg == "MyGroup":
            if is_group:
                group_id = event.source.group_id
                line_bot_api.push_message(user_id, TextSendMessage(text=admin_my_group(group_id)))
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_GROUP_ID_REPLY))
            return

    # --- Registration (kept as text — first-time user has no Rich Menu yet) ---
    if msg.startswith("#regis"):
        try:
            lines = [line.strip() for line in msg.split('\n') if line.strip()]
            
            if len(lines) < 5:
                raise ValueError(REGISTRATION_ERROR_MISSING_DATA)
        
            full_name = lines[1].split() 
            if len(full_name) < 2:
                raise ValueError(REGISTRATION_ERROR_NAME_INCOMPLETE)
            
            fname = full_name[0]
            lname = " ".join(full_name[1:])
            
            nname = lines[2]
            tel = lines[3]
            email = lines[4]
            
            if not check_nickname_available(nname, user_id):
                raise ValueError(registration_nickname_taken(nname))

            register_user(user_id, fname, lname, nname, tel, email)
            
            # Link member Rich Menu after successful registration
            try:
                from app.modules.rich_menu import link_member_menu
                link_member_menu(user_id)
            except Exception as e:
                print(f"Rich Menu link error (non-critical): {e}")
            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=registration_success(nname, email)))

        except ValueError as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=registration_error_prompt(str(e))))
        return

    # --- Slip Submission (step 2 of payment flow, triggered after image upload) ---
    if msg.startswith("#โอน"):
        if is_group: return
        if not require_registration(user_id, event.reply_token): return
        
        _process_transfer_submission(event, msg, user_id)


# ============================================================
# IMAGE MESSAGE HANDLER
# ============================================================

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    if event.source.type == "group": return
    user_id = event.source.user_id

    if not check_is_registered(user_id):
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=REGISTRATION_PROMPT_WITH_FORMAT))
        return

    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        file_stream = io.BytesIO()
        for chunk in message_content.iter_content():
            file_stream.write(chunk)
        file_stream.seek(0)
        
        file_id = save_slip_image(file_stream, f"{event.message.id}.jpg")
        save_temp_slip_id(user_id, file_id)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=SLIP_SUBMISSION_FLOW_STEP2))

    except Exception as e:
        print(f"Error saving image: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=SLIP_SAVE_ERROR))


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _process_transfer_submission(event, msg, user_id):
    try:
        data = validate_slip_format(msg)
        user = get_user(user_id)
        if not user:
             line_bot_api.reply_message(event.reply_token, TextSendMessage(text=USER_NOT_FOUND))
             return

        # Check Name
        registered_nickname = user.get('nickname', '')
        if data['nickname'].strip().lower() != registered_nickname.strip().lower():
            raise ValueError(SLIP_SUBMISSION_NICKNAME_MISMATCH)

        current_next_due = user.get('next_due_date')
        
        if current_next_due:
            input_due_date = calculate_next_due_date_from_text(data['billing'], data['months'])
            
            if input_due_date:
                if input_due_date <= current_next_due:
                    last_paid_month = current_next_due - timedelta(days=20) 
                    paid_str = get_thai_month_year(last_paid_month)
                    raise ValueError(slip_submission_duplicate(paid_str))
            else:
                raise ValueError(SLIP_SUBMISSION_INVALID_DATE)

        # Check Pending Slip
        file_id = user.get('temp_slip_id')
        if not file_id:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=SLIP_SUBMISSION_MISSING_IMAGE))
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
            TextSendMessage(text=admin_notify_transfer_header(data['nickname'], full_info)),
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url),
            FlexSendMessage(alt_text="บิลแจ้งโอน", contents=flex_msg)
        ])
        
        users_col.update_one(
            {"user_id": user_id}, 
            {"$unset": {"temp_slip_id": "", "slip_uploaded_at": ""}}
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=SLIP_SUBMISSION_SUCCESS))

    except ValueError as e:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=str(e)))
    except Exception as e:
        print(f"System Error: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=SLIP_SUBMISSION_SYSTEM_ERROR))


def _process_admin_view_slip(event, msg):
    """
    Admin views a specific transaction's slip image
    Format: #ดูสลิป [ชื่อเล่น] [เดือน] [ปี]
    Example: #ดูสลิป ฝ้าย ม.ค. 68
    """
    try:
        parts = msg.replace("#ดูสลิป", "").strip()
        if not parts:
            raise ValueError(ADMIN_VIEW_SLIP_USAGE_ERROR)

        tokens = parts.split()
        if len(tokens) < 3:
            raise ValueError(ADMIN_VIEW_SLIP_USAGE_ERROR)

        nickname = tokens[0]
        month_year_text = " ".join(tokens[1:])

        parsed = parse_month_year(month_year_text)
        if not parsed:
            raise ValueError(ADMIN_VIEW_SLIP_FORMAT_ERROR)

        month, year = parsed

        slip, status = get_transaction_slip_by_details(nickname, month, year)

        if status == "not_found_user":
            raise ValueError(admin_view_slip_not_found_user(nickname))
        elif status == "not_found_tx":
            from app.utils.const import THAI_MONTHS
            month_str = THAI_MONTHS[month - 1]
            thai_year = str((year + 543) % 100)
            raise ValueError(admin_view_slip_not_found_tx(nickname, month_str, thai_year))
        elif status == "not_found_slip":
            raise ValueError(ADMIN_VIEW_SLIP_NO_SLIP)
        elif status == "invalid_month":
            raise ValueError(ADMIN_VIEW_SLIP_INVALID_MONTH)

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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_VIEW_SLIP_SYSTEM_ERROR))


def _process_admin_delete_prompt(event, msg):
    """
    Admin deletes transaction history
    Format: #ลบประวัติ [ชื่อเล่น]
    """
    try:
        parts = msg.replace("#ลบประวัติ", "").strip()
        if not parts:
            raise ValueError(ADMIN_DELETE_USAGE_ERROR)

        nickname = parts.strip()
        users = find_users_by_nickname(nickname)

        if not users:
            raise ValueError(admin_delete_not_found_user(nickname))

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
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ADMIN_DELETE_SYSTEM_ERROR))


def require_registration(user_id, reply_token):
    if not check_is_registered(user_id):
        line_bot_api.reply_message(reply_token, TextSendMessage(text=REQUIRE_REGISTRATION_PROMPT))
        return False
    return True