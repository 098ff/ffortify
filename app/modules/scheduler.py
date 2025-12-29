from apscheduler.schedulers.background import BackgroundScheduler
from linebot.models import TextSendMessage
from app.modules.line_api import line_bot_api
from app.setup.database import get_all_users, cleanup_expired_slips
from app.setup.config import Config
from app.utils.date_time import get_thai_time

scheduler = BackgroundScheduler(timezone="Asia/Bangkok")

def monthly_reminder():
    if Config.GROUP_ID_TO_ALERT:
        try:
            line_bot_api.push_message(
                Config.GROUP_ID_TO_ALERT,
                TextSendMessage(text="📢 แจ้งเตือน: วันที่ 13 แล้ว พี่ ๆ อย่าลืมจ่ายค่า Spotify น้า")
            )
            print("Reminder sent.")
        except Exception as e:
            print(f"Reminder Error: {e}")

def month_end_check():
    if not Config.GROUP_ID_TO_ALERT: return
    
    now = get_thai_time().replace(tzinfo=None)
    unpaid_users = []
    
    for user in get_all_users():
        # ถ้า next_due_date น้อยกว่าตอนนี้ แปลว่าเลยกำหนดจ่ายแล้ว (ค้างชำระ)
        if user.get('next_due_date') and user['next_due_date'] <= now:
            unpaid_users.append(user.get('nickname', 'Unknown'))
            
    if unpaid_users:
        msg = "⚠️ สิ้นเดือนแล้ว! มียอดค้างชำระจาก:\n" + "\n".join(unpaid_users)
        line_bot_api.push_message(Config.GROUP_ID_TO_ALERT, TextSendMessage(text=msg))

def start_scheduler():
    # วันที่ 13 เวลา 09:00
    scheduler.add_job(monthly_reminder, 'cron', day=13, hour=9, minute=0)
    # วันที่ 28 เวลา 18:00
    scheduler.add_job(month_end_check, 'cron', day=28, hour=18, minute=0)
    # Delte expired temp slips every hour
    scheduler.add_job(cleanup_expired_slips, 'interval', hours=1)
    scheduler.start()