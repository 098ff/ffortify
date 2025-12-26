from datetime import datetime
import pytz

def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)

def format_date(date_obj):
    if not date_obj:
        return "-"
    return date_obj.strftime('%d/%m/%Y')