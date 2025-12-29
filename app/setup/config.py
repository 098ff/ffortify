import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    PORT = int(os.getenv('PORT'))

    CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
    CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
    MONGO_URI = os.getenv('MONGO_URI')
    ADMIN_USER_ID = os.getenv('ADMIN_USER_ID')
    GROUP_ID_TO_ALERT = os.getenv('GROUP_ID_TO_ALERT')

    LINE_BOT_BASIC_ID = os.getenv('LINE_BOT_BASIC_ID')

    MONTHLY_PRICE = 41.5  # ราคาต่อเดือน (บาท)
    ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")

    SLIP_TIMEOUT_HOURS = int(os.environ.get('SLIP_TIMEOUT_HOURS', 1))