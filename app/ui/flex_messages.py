from urllib.parse import quote
from app.setup.config import Config

def get_main_menu_flex():
    text_message = quote("เริ่มจ่ายเงิน")
    payment_url = f"https://line.me/R/oaMessage/{Config.LINE_BOT_BASIC_ID}/?text={text_message}"
    
    return {
        "type": "bubble",
        "hero": {"type": "image", "url": "https://images.unsplash.com/photo-1614680376593-902f74cf0d41?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80", "size": "full", "aspectRatio": "20:13", "aspectMode": "cover"},
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🎵 Spotify Payment Bot", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "น้องฝ้ายมารายงานตัวแล้วค่ะ มีอะไรให้ช่วยมั้ยคะ?", "wrap": True, "color": "#666666", "size": "sm"}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "color": "#1DB954", "action": {"type": "uri", "label": "💸 ชำระเงิน (ส่วนตัว)", "uri": payment_url}},
                {"type": "button", "style": "secondary", "action": {"type": "message", "label": "🔍 เช็คยอดค้าง", "text": "เช็คยอด"}}
            ]
        }
    }

def create_admin_flex(name, amount, months, bank, time, bill_month, tx_id):
    display_amount = f"{amount:g}"
    return {
        "type": "bubble",
        "header": {"type": "box", "layout": "vertical", "contents": [{"type": "text", "text": "📝 รายการโอนเงินใหม่", "weight": "bold", "color": "#1DB954"}]},
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": f"User: {name}", "size": "lg", "weight": "bold"},
                {"type": "separator", "margin": "md"},
                {"type": "text", "text": f"💰 ยอดโอน: {display_amount} บาท"},
                {"type": "text", "text": f"📅 จำนวน: {months} เดือน"},
                {"type": "text", "text": f"🧾 บิลของ: {bill_month}", "color": "#0000ff", "weight": "bold"},
                {"type": "text", "text": f"🏦 ธนาคาร: {bank}"},
                {"type": "text", "text": f"⏰ เวลาโอน: {time}"}
            ]
        },
        "footer": {
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "action": {"type": "postback", "label": "รับยอด", "data": f"action=approve&txid={tx_id}"}},
                {"type": "button", "style": "secondary", "action": {"type": "postback", "label": "ยกเลิก", "data": f"action=reject&txid={tx_id}"}}
            ]
        }
    }