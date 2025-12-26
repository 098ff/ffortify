from linebot.models import FollowEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler

@handler.add(FollowEvent)
def handle_follow(event):
    reply_txt = (
        "ยินดีต้อนรับสู่ Spotify Bot ค่า 🎉\n\n"
        "📝 **ลงทะเบียนครั้งแรก (เก็บข้อมูลครั้งเดียว)**\n"
        "พิมพ์: `#regis [ชื่อจริง] [นามสกุล] [ชื่อเล่น] [เบอร์โทร] [อีเมล]`\n\n"
        "ตัวอย่าง:\n"
        "#regis สมชาย ใจดี มิก 0812345678 mik@email.com"
    )
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_txt))