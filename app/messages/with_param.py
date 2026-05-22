# Dynamic messages (with receive parameters)

def admin_already_processed(status_msg: str) -> str:
    return f"⚠️ รายการนี้ถูก '{status_msg}' ไปแล้วค่ะ"

def admin_push_approved(thai_date_str: str) -> str:
    return f"✅ แอดมินพี่ฝ้ายรับยอดแล้ว!\n(รอบบิลถัดไป: {thai_date_str})"

def admin_reply_approved(thai_date_str: str) -> str:
    return f"บันทึกยอดเรียบร้อย (รอบบิลถัดไป: {thai_date_str})"

def admin_soft_delete_success(target_name: str, count: int) -> str:
    return f"✅ Soft Delete สำเร็จ!\n\nซ่อนประวัติของ '{target_name}' จำนวน {count} รายการ\n(ข้อมูลยังอยู่ในระบบ สามารถกู้คืนได้)"

def admin_hard_delete_success(target_name: str, count: int) -> str:
    return f"🗑️ Hard Delete สำเร็จ!\n\nลบประวัติของ '{target_name}' จำนวน {count} รายการถาวร\n⚠️ ไม่สามารถกู้คืนได้"

def admin_check_not_found(target_nick: str) -> str:
    return f"❌ ไม่พบบัญชีผู้ใช้งานนี้: {target_nick}"

def admin_check_item(first_name: str, nickname: str, status: str) -> str:
    return f"- {first_name} ({nickname}) : บิลถัดไป {status}\n"

def admin_my_id(user_id: str) -> str:
    return f"User ID: {user_id}"

def admin_my_group(group_id: str) -> str:
    return f"Group ID: {group_id}"

def registration_nickname_taken(nname: str) -> str:
    return f"❌ ชื่อเล่น '{nname}' มีคนใช้แล้วค่ะ!"

def registration_success(nname: str, email: str) -> str:
    return (
        f"✅ ลงทะเบียนสำเร็จ!\n"
        f"ยินดีต้อนรับพี่ {nname} ({email})\n\n"
        f"น้องฝอยพร้อมดูแลค้าบ 🥸☝🏼\n"
        f"กดเมนูด้านล่างเพื่อเริ่มใช้งานได้เลย 👇🏼"
    )

def registration_error_prompt(err_msg: str) -> str:
    return (
        f"❌ {err_msg}\n\n"
        "ตัวอย่างการพิมพ์:\n"
        "#regis\n"
        "ชนัดดา คนชม\n"
        "ฝ้าย\n"
        "0812345678\n"
        "fforfaii@gmail.com"
    )

def slip_submission_duplicate(paid_str: str) -> str:
    return (
        f"❌ ยอดนี้จ่ายซ้ำค่ะ!\n\n"
        f"ข้อมูลล่าสุดพี่จ่ายถึงรอบเดือน **{paid_str}** แล้ว"
    )

def admin_view_slip_not_found_user(nickname: str) -> str:
    return f"❌ ไม่พบสมาชิกชื่อ '{nickname}' ในระบบ"

def admin_view_slip_not_found_tx(nickname: str, month_str: str, thai_year: str) -> str:
    return f"❌ ไม่พบรายการของ '{nickname}' ในเดือน {month_str} {thai_year}"

def admin_delete_not_found_user(nickname: str) -> str:
    return f"❌ ไม่พบสมาชิกชื่อ '{nickname}' ในระบบ"

def admin_notify_transfer_header(nickname: str, full_info: str) -> str:
    return f"📨 แจ้งโอนจาก {nickname}\n{full_info}"
