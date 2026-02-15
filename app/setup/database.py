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

def create_transaction(tx_id, user_id, amount, months, billing):
    """สร้าง Transaction (Lean schema)"""
    data = {
        "_id": tx_id,
        "uid": user_id,
        "amount": amount,
        "cnt_month": months,
        "billing": billing,
        "status": "pending",
        "created_at": datetime.now()
    }
    transactions_col.insert_one(data)


def get_transaction(tx_id):
    return transactions_col.find_one({"_id": tx_id})


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
        from app.setup.database import fs 
        fs.delete(file_id)
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
