from linebot.models import FollowEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler
from app.setup.database import check_is_registered

@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id

    reply_txt = (
        "สวัสดีค่า น้องฝอยพร้อมให้บริการค้าบ 🥸☝🏼\n\n"
        "📝 ลงทะเบียนครั้งแรก\n"
        "พิมพ์: \n#regis\n[ชื่อจริง] [นามสกุล]\n[ชื่อเล่น]\n[เบอร์โทร]\n[อีเมล]\n\n"
        "ตัวอย่าง:\n"
        "#regis\nชนัดดา คนชม\nฝอฝ้าย\n0812345678\nchanatdakc@gmail.com"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))

    # If already registered, link the member Rich Menu
    if check_is_registered(user_id):
        try:
            from app.modules.rich_menu import link_member_menu
            link_member_menu(user_id)
        except Exception as e:
            print(f"Rich Menu link on follow error (non-critical): {e}")