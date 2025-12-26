from linebot import LineBotApi, WebhookHandler
from app.config import Config

line_bot_api = LineBotApi(Config.CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(Config.CHANNEL_SECRET)