from linebot.models import FollowEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler

@handler.add(FollowEvent)
def handle_follow(event):
    reply_txt = (
        "สวัสดีค่า น้องฝอยพร้อมให้บริการค้าบ 🥸☝🏼\n\n"
        "📝 ลงทะเบียนครั้งแรก\n"
        "พิมพ์: \n#regis\n[ชื่อจริง]\n[นามสกุล]\n[ชื่อเล่น]\n[เบอร์โทร]\n[อีเมล]\n\n"
        "ตัวอย่าง:\n"
        "#regis\nชนัดดา คนชม\nฝอฝ้าย\n0812345678\nchanatdakc@gmail.com"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))