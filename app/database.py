from datetime import datetime
from pymongo import MongoClient
import bson.binary
from bson.objectid import ObjectId
from app.config import Config

# เชื่อมต่อ Database
client = MongoClient(Config.MONGO_URI)
db = client['spotify_bot'] # เช็คชื่อ DB ให้ตรงกับของคุณ

# Collections
users_col = db['users']
transactions_col = db['transactions']
slips_col = db['slips']

# --- User Functions ---

def check_nickname_available(nickname, user_id):
    """
    เช็คว่าชื่อเล่นว่างไหม (Case Insensitive)
    คืนค่า True ถ้าว่าง (หรือเป็นชื่อเดิมของตัวเอง), False ถ้ามีคนอื่นใช้แล้ว
    """
    existing_user = users_col.find_one({
        "nickname": {"$regex": f"^{nickname}$", "$options": "i"}, 
        "user_id": {"$ne": user_id} 
    })
    return existing_user is None

def register_user(user_id, firstname, lastname, nickname, tel, email):
    """ลงทะเบียน (เพิ่มเบอร์, อีเมล และเช็คชื่อซ้ำก่อนเรียกฟังก์ชันนี้)"""
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
    """เช็คสถานะลงทะเบียน"""
    user = users_col.find_one({"user_id": user_id})
    return user is not None and user.get("is_registered", False) is True

def get_user(user_id):
    """ดึงข้อมูล User"""
    return users_col.find_one({'user_id': user_id})

def get_all_users():
    """ดึง User ทั้งหมด (สำหรับ Scheduler)"""
    return users_col.find()

def find_users_by_nickname(nickname):
    """ค้นหา User จากชื่อเล่น (Admin Search)"""
    regex_query = {"$regex": f"^{nickname}$", "$options": "i"}
    return list(users_col.find({"nickname": regex_query}))

def update_user_payment(user_id, transaction_id, new_paid_until):
    """อัปเดตวันหมดอายุ และ Transaction ID ล่าสุด"""
    users_col.update_one(
        {'user_id': user_id},
        {'$set': {
            'paid_until': new_paid_until,
            'latest_txd': transaction_id 
        }}
    )

def save_temp_slip_id(user_id, file_id):
    """ฝาก ID รูปไว้ชั่วคราว"""
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"temp_slip_id": file_id}},
        upsert=True 
    )

# --- Transaction Functions ---

def create_transaction(tx_id, user_id, amount, months, billing_txt, bank, slip_datetime):
    """สร้างรายการ (Lean Schema)"""
    data = {
        "_id": tx_id,
        "uid": user_id,          
        "amount": amount,
        "cnt_month": months,     
        "billing_txt": billing_txt, 
        "bank": bank,
        "slip_datetime": slip_datetime,
        "status": "pending",     
        "created_at": datetime.now()
    }
    transactions_col.insert_one(data)

def get_transaction(tx_id):
    return transactions_col.find_one({"_id": tx_id})

def complete_transaction(tx_id):
    transactions_col.update_one(
        {"_id": tx_id},
        {"$set": {"status": "completed", "approved_at": datetime.now()}}
    )

def reject_transaction(tx_id):
    transactions_col.update_one(
        {"_id": tx_id},
        {"$set": {"status": "rejected", "rejected_at": datetime.now()}}
    )

# --- Slip (Image) Functions ---

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
    except:
        return None