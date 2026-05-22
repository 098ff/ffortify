from datetime import datetime, timedelta
from pymongo import MongoClient
import bson.binary
from bson.objectid import ObjectId

from app.setup.config import Config

# -------------------------------
# Database Connection
# -------------------------------
client = MongoClient(Config.MONGO_URI)
db = client["spotify_bot"] 

# Collections
users_col = db["users"]
transactions_col = db["transactions"]
slips_col = db["slips"]

# -------------------------------
# User Functions
# -------------------------------

def check_nickname_available(nickname, user_id):
    """
    เช็คว่าชื่อเล่นว่างไหม (Case Insensitive)
    True = ว่าง / เป็นชื่อเดิมตัวเอง
    False = มีคนอื่นใช้แล้ว
    """
    existing_user = users_col.find_one({
        "nickname": {"$regex": f"^{nickname}$", "$options": "i"},
        "user_id": {"$ne": user_id}
    })
    return existing_user is None


def register_user(user_id, firstname, lastname, nickname, tel, email):
    """ลงทะเบียนผู้ใช้"""
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "first_name": firstname,
            "last_name": lastname,
            "nickname": nickname,
            "tel_number": tel,
            "email": email,
            "is_registered": True,
            "registered_at": datetime.now()
        }},
        upsert=True
    )


def check_is_registered(user_id):
    """เช็คว่าผู้ใช้ลงทะเบียนแล้วหรือยัง"""
    user = users_col.find_one({"user_id": user_id})
    return user is not None and user.get("is_registered") is True


def get_user(user_id):
    """ดึงข้อมูล User"""
    return users_col.find_one({"user_id": user_id})


def get_all_users():
    """ดึง User ทั้งหมด (ใช้กับ Scheduler)"""
    return users_col.find()


def find_users_by_nickname(nickname):
    """ค้นหา User จากชื่อเล่น (Admin)"""
    regex_query = {"$regex": f"^{nickname}$", "$options": "i"}
    return list(users_col.find({"nickname": regex_query}))


def update_user_payment(user_id, tx_id, new_due_date):
    """อัปเดตวันครบกำหนดชำระ"""
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "next_due_date": new_due_date,
            "last_transaction_id": tx_id
        }}
    )

# -------------------------------
# Transaction Functions
# -------------------------------

def create_transaction(tx_id, user_id, amount, months, billing, slip_id=None):
    """สร้าง Transaction (Lean schema)"""
    data = {
        "_id": tx_id,
        "uid": user_id,
        "amount": amount,
        "cnt_month": months,
        "billing": billing,
        "slip_id": slip_id,
        "status": "pending",
        "is_deleted": False,
        "created_at": datetime.now()
    }
    transactions_col.insert_one(data)


def get_transaction(tx_id):
    return transactions_col.find_one({"_id": tx_id, "is_deleted": {"$ne": True}})


def complete_transaction(tx_id):
    transactions_col.update_one(
        {"_id": tx_id},
        {"$set": {
            "status": "completed",
            "approved_at": datetime.now()
        }}
    )


def reject_transaction(tx_id):
    transactions_col.update_one(
        {"_id": tx_id},
        {"$set": {
            "status": "rejected",
            "rejected_at": datetime.now()
        }}
    )


def get_user_transactions(user_id):
    """
    ดึง Transaction ทั้งหมดของ User (ไม่รวม soft-deleted)
    เรียงจากใหม่ -> เก่า
    เฉพาะ user ของตัวเองเท่านั้น (security)
    """
    return list(transactions_col.find(
        {"uid": user_id, "is_deleted": {"$ne": True}},
        sort=[("created_at", -1)]
    ))


def get_all_registered_users():
    """ดึง User ที่ลงทะเบียนแล้วทั้งหมด"""
    return list(users_col.find({"is_registered": True}))


def get_all_member_statuses():
    """
    ดึงสถานะสมาชิกทุกคน พร้อมข้อมูลการจ่ายล่าสุด
    Returns: list of dicts with user info + latest transaction info
    """
    members = list(users_col.find({"is_registered": True}))
    result = []

    for member in members:
        user_id = member.get("user_id")
        nickname = member.get("nickname", "ไม่ทราบ")
        first_name = member.get("first_name", "")
        next_due = member.get("next_due_date")

        # หา Transaction ล่าสุดที่ approved
        latest_tx = transactions_col.find_one(
            {"uid": user_id, "status": "completed", "is_deleted": {"$ne": True}},
            sort=[("approved_at", -1)]
        )

        last_paid_date = latest_tx.get("approved_at") if latest_tx else None
        
        # เช็คว่า overdue หรือไม่
        is_overdue = False
        if next_due:
            now = datetime.now()
            if next_due <= now:
                is_overdue = True

        result.append({
            "user_id": user_id,
            "first_name": first_name,
            "nickname": nickname,
            "next_due_date": next_due,
            "last_paid_date": last_paid_date,
            "is_overdue": is_overdue,
            "billing": latest_tx.get("billing", "-") if latest_tx else "-"
        })

    return result


def soft_delete_transactions(user_id):
    """Soft Delete - mark all transactions of a user as deleted"""
    result = transactions_col.update_many(
        {"uid": user_id, "is_deleted": {"$ne": True}},
        {"$set": {
            "is_deleted": True,
            "deleted_at": datetime.now()
        }}
    )
    return result.modified_count


def hard_delete_transactions(user_id):
    """Hard Delete - permanently remove all transactions of a user from MongoDB"""
    result = transactions_col.delete_many({"uid": user_id})
    return result.deleted_count


def get_transaction_slip_by_details(nickname, month, year):
    """
    ค้นหาสลิป Transaction จาก ชื่อเล่น, เดือน, ปี (รองรับการจ่ายแบบเหมาหลายเดือน)
    Returns: slip file_doc or None, status_code
    """
    # หา user จาก nickname
    user = users_col.find_one({
        "nickname": {"$regex": f"^{nickname}$", "$options": "i"},
        "is_registered": True
    })
    if not user:
        return None, "not_found_user"

    user_id = user.get("user_id")

    # ดึง transaction ที่สำเร็จทั้งหมดของผู้ใช้
    transactions = list(transactions_col.find({
        "uid": user_id,
        "status": "completed",
        "is_deleted": {"$ne": True}
    }, sort=[("created_at", -1)]))

    if not transactions:
        return None, "not_found_tx"

    from app.utils.date_time import parse_month_year

    # กรองหา transaction ที่ครอบคลุมเดือนและปีที่ต้องการ
    matching_tx = None
    for tx in transactions:
        billing_str = tx.get("billing", "")
        cnt_month = int(tx.get("cnt_month", 1))
        
        # ล้างช่องว่างและแปลงคำเชื่อม
        clean_txt = billing_str.replace("ถึง", "-").replace(" ", "")
        start_str = clean_txt.split("-")[0]
        
        parsed = parse_month_year(start_str)
        if not parsed:
            continue
            
        start_month, start_year = parsed
        
        # ตรวจสอบว่า target อยู่ในครอบคลุมของช่วงเดือนนี้หรือไม่
        is_match = False
        for i in range(cnt_month):
            current_m = start_month + i
            y_offset = (current_m - 1) // 12
            m_val = (current_m - 1) % 12 + 1
            y_val = start_year + y_offset
            if m_val == month and y_val == year:
                is_match = True
                break
                
        if is_match:
            matching_tx = tx
            break

    if not matching_tx:
        return None, "not_found_tx"

    slip_id = matching_tx.get("slip_id")
    if not slip_id:
        return None, "not_found_slip"

    try:
        slip = slips_col.find_one({"_id": ObjectId(slip_id)})
        if slip:
            return slip, "found"
    except Exception:
        pass

    return None, "not_found_slip"


# -------------------------------
# Slip (Image) Functions
# -------------------------------

def save_temp_slip_id(user_id, file_id):
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {
            "temp_slip_id": file_id,
            "slip_uploaded_at": datetime.now()
        }}
    )


def save_slip_image(file_stream, filename):
    file_bytes = file_stream.read()
    file_doc = {
        "filename": filename,
        "data": bson.binary.Binary(file_bytes),
        "created_at": datetime.now()
    }
    result = slips_col.insert_one(file_doc)
    return str(result.inserted_id)


def get_slip_image(file_id):
    try:
        return slips_col.find_one({"_id": ObjectId(file_id)})
    except Exception:
        return None


def delete_file_from_storage(file_id):
    """
    ลบไฟล์จริง 
    """
    try:
        slips_col.delete_one({"_id": ObjectId(file_id)})
    except Exception as e:
        print(f"Error deleting file {file_id}: {e}")


def cleanup_expired_slips():
    """ลบสลิปที่ค้างเกินเวลาที่กำหนด"""
    timeout_hours = Config.SLIP_TIMEOUT_HOURS
    cutoff_time = datetime.now() - timedelta(hours=timeout_hours)

    expired_users = users_col.find({
        "temp_slip_id": {"$exists": True},
        "slip_uploaded_at": {"$lt": cutoff_time}
    })

    count = 0
    for user in expired_users:
        file_id = user.get("temp_slip_id")
        if file_id:
            delete_file_from_storage(file_id)
            users_col.update_one(
                {"_id": user["_id"]},
                {"$unset": {
                    "temp_slip_id": "",
                    "slip_uploaded_at": ""
                }}
            )
            count += 1

    if count > 0:
        print(f"🧹 Cleaned up {count} expired slips.")
