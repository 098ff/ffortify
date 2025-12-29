from urllib.parse import quote
from app.setup.config import Config

def get_main_menu_flex():
    text_message = quote("เริ่มจ่ายเงิน")
    payment_url = f"https://line.me/R/oaMessage/{Config.LINE_BOT_BASIC_ID}/?{text_message}"
    
    return {
        "type": "bubble",
        "hero": {"type": "image", "url": "https://i.postimg.cc/t4mCCS29/Gemini-Generated-Image-mouu6imouu6imouu.png", "size": "full", "aspectRatio": "20:13", "aspectMode": "cover"},
        "body": {
            "type": "box", "layout": "vertical",
            "contents": [
                {"type": "text", "text": "🎵 N'foii Payment Bot", "weight": "bold", "size": "xl"},
                {"type": "text", "text": "น้องฝอยมาแล้ววว มีอะไรให้ช่วยมั้ยค้าบ?", "wrap": True, "color": "#666666", "size": "sm"}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "color": "#831FA4", "action": {"type": "uri", "label": "💸 ชำระเงิน", "uri": payment_url}},
                {"type": "button", "style": "secondary", "action": {"type": "message", "label": "🔍 เช็คยอด", "text": "เช็คยอด"}}
            ]
        }
    }

def create_admin_flex(name, amount, months, bill_month, tx_id):
    display_amount = f"{amount:g}"
    
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "รายการโอนเงินใหม่",
                    "weight": "bold",
                    "color": "#731B98",
                    "size": "sm"
                },
                {
                    "type": "text",
                    "text": name,
                    "weight": "bold",
                    "size": "xxl",
                    "margin": "md"
                },
                {
                    "type": "separator",
                    "margin": "xxl"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "xxl",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "ยอดโอน",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                },
                                {
                                    "type": "text",
                                    "text": f"฿{display_amount}",
                                    "size": "sm",
                                    "color": "#111111",
                                    "align": "end"
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "จำนวน",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                },
                                {
                                    "type": "text",
                                    "text": f"{months} เดือน",
                                    "size": "sm",
                                    "color": "#111111",
                                    "align": "end"
                                }
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "ช่วงเดือน",
                                    "size": "sm",
                                    "color": "#555555",
                                    "flex": 0
                                },
                                {
                                    "type": "text",
                                    "text": bill_month,
                                    "size": "sm",
                                    "color": "#111111",
                                    "align": "end"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#831FA4",
                    "action": {
                        "type": "postback",
                        "label": "รับยอด",
                        "data": f"action=approve&txid={tx_id}"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "ยกเลิก",
                        "data": f"action=reject&txid={tx_id}"
                    }
                }
            ]
        },
        "styles": {
            "footer": {
                "separator": True
            }
        }
    }