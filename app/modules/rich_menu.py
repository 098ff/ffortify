"""
Rich Menu Module
- Creates and manages Rich Menus for Member and Admin via LINE Messaging API
- Stores Rich Menu IDs in MongoDB for persistence
- Links appropriate menu to users based on their role
"""
import os
import requests
from app.setup.config import Config
from app.setup.database import db

# Collection for storing rich menu IDs
rich_menu_col = db["rich_menus"]

# -----------------------------------------------
# Rich Menu Image Paths (relative to project root)
# -----------------------------------------------
DEFAULT_MENU_IMAGE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "default_rich_menu.png")
MEMBER_MENU_IMAGE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "member_rich_menu.png")
ADMIN_MENU_IMAGE = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "admin_rich_menu.png")

# -----------------------------------------------
# LINE Messaging API Headers
# -----------------------------------------------
HEADERS = {
    "Authorization": f"Bearer {Config.CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

HEADERS_IMAGE = {
    "Authorization": f"Bearer {Config.CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "image/png"
}

LINE_API_BASE = "https://api.line.me/v2/bot"


# -----------------------------------------------
# Default Rich Menu Definition (2 areas)
# Layout: [ลงทะเบียน] [คำสั่ง]
# -----------------------------------------------
DEFAULT_RICH_MENU = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "Default Menu",
    "chatBarText": "📝 เมนูเริ่มต้น",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "ลงทะเบียน",
                "data": "action=start_registration",
                "displayText": "📝 เริ่มการลงทะเบียน"
            }
        },
        {
            "bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "คำสั่ง",
                "data": "action=default_help",
                "displayText": "❓ วิธีใช้และคำสั่ง"
            }
        }
    ]
}


# -----------------------------------------------
# Member Rich Menu Definition (3 areas)
# Layout: [ดูรายการ] [ส่งสลิป] [คำสั่ง]
# -----------------------------------------------
MEMBER_RICH_MENU = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "Member Menu",
    "chatBarText": "📋 เมนูสมาชิก",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "postback",
                "label": "ดูรายการ",
                "data": "action=my_transactions",
                "displayText": "📋 ดูรายการของฉัน"
            }
        },
        {
            "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
            "action": {
                "type": "postback",
                "label": "ส่งสลิป",
                "data": "action=start_payment",
                "displayText": "💸 ส่งสลิปชำระเงิน"
            }
        },
        {
            "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
            "action": {
                "type": "postback",
                "label": "คำสั่ง",
                "data": "action=member_help",
                "displayText": "❓ ดูคำสั่งทั้งหมด"
            }
        }
    ]
}


# -----------------------------------------------
# Admin Rich Menu Definition (4 areas, 2x2 grid)
# Layout: [สถานะสมาชิก] [ลบประวัติ]
#         [ดูสลิป      ] [คำสั่ง   ]
# -----------------------------------------------
ADMIN_RICH_MENU = {
    "size": {"width": 2500, "height": 1686},
    "selected": True,
    "name": "Admin Menu",
    "chatBarText": "🔧 เมนูแอดมิน",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "สถานะสมาชิก",
                "data": "action=admin_all_status",
                "displayText": "📊 ดูสถานะสมาชิกทั้งหมด"
            }
        },
        {
            "bounds": {"x": 1250, "y": 0, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "ลบประวัติ",
                "data": "action=admin_delete_menu",
                "displayText": "🗑️ ลบประวัติรายการ"
            }
        },
        {
            "bounds": {"x": 0, "y": 843, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "ดูสลิป",
                "data": "action=admin_view_slip_prompt",
                "displayText": "🖼️ ดูสลิปรายการ"
            }
        },
        {
            "bounds": {"x": 1250, "y": 843, "width": 1250, "height": 843},
            "action": {
                "type": "postback",
                "label": "คำสั่ง",
                "data": "action=admin_help",
                "displayText": "❓ ดูคำสั่งทั้งหมด"
            }
        }
    ]
}


def _create_rich_menu(menu_body):
    """Create a Rich Menu via LINE API and return the rich_menu_id"""
    resp = requests.post(
        f"{LINE_API_BASE}/richmenu",
        headers=HEADERS,
        json=menu_body
    )
    if resp.status_code == 200:
        return resp.json().get("richMenuId")
    else:
        print(f"❌ Failed to create rich menu: {resp.status_code} {resp.text}")
        return None


def _upload_rich_menu_image(rich_menu_id, image_path):
    """Upload an image to a Rich Menu"""
    if not os.path.exists(image_path):
        print(f"❌ Rich Menu image not found: {image_path}")
        return False
    
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers=HEADERS_IMAGE,
            data=f.read()
        )
    
    if resp.status_code == 200:
        return True
    else:
        print(f"❌ Failed to upload rich menu image: {resp.status_code} {resp.text}")
        return False


def _link_rich_menu_to_user(user_id, rich_menu_id):
    """Link a Rich Menu to a specific user"""
    resp = requests.post(
        f"{LINE_API_BASE}/user/{user_id}/richmenu/{rich_menu_id}",
        headers=HEADERS
    )
    if resp.status_code == 200:
        print(f"✅ Rich Menu linked to user: {user_id[:10]}...")
        return True
    else:
        print(f"❌ Failed to link rich menu: {resp.status_code} {resp.text}")
        return False


def _delete_rich_menu(rich_menu_id):
    """Delete a Rich Menu by ID"""
    resp = requests.delete(
        f"{LINE_API_BASE}/richmenu/{rich_menu_id}",
        headers=HEADERS
    )
    return resp.status_code == 200


def _get_stored_menu_id(role):
    """Get stored Rich Menu ID from database"""
    doc = rich_menu_col.find_one({"role": role})
    return doc.get("rich_menu_id") if doc else None


def _store_menu_id(role, rich_menu_id):
    """Store Rich Menu ID in database"""
    rich_menu_col.update_one(
        {"role": role},
        {"$set": {"rich_menu_id": rich_menu_id}},
        upsert=True
    )


def _set_default_rich_menu(rich_menu_id):
    """Set a Rich Menu as the global default for all users who don't have a linked menu"""
    resp = requests.post(
        f"{LINE_API_BASE}/user/all/richmenu/{rich_menu_id}",
        headers=HEADERS
    )
    if resp.status_code == 200:
        print(f"✅ Set global default Rich Menu to: {rich_menu_id}")
        return True
    else:
        print(f"❌ Failed to set global default Rich Menu: {resp.status_code} {resp.text}")
        return False


def setup_default_rich_menu():
    """Create and store the Default (Unregistered) Rich Menu (if not already existing)"""
    existing_id = _get_stored_menu_id("default")
    
    # Verify existing menu is still valid on LINE's side
    if existing_id:
        check = requests.get(
            f"{LINE_API_BASE}/richmenu/{existing_id}",
            headers=HEADERS
        )
        if check.status_code == 200:
            print("✅ Default Rich Menu already exists, skipping creation.")
            # Ensure it is still set as the default menu on LINE
            _set_default_rich_menu(existing_id)
            return existing_id
        else:
            print("⚠️ Stored Default Rich Menu ID is stale, recreating...")
    
    menu_id = _create_rich_menu(DEFAULT_RICH_MENU)
    if not menu_id:
        return None
    
    if _upload_rich_menu_image(menu_id, DEFAULT_MENU_IMAGE):
        _store_menu_id("default", menu_id)
        _set_default_rich_menu(menu_id)
        print(f"✅ Default Rich Menu created & set as global default: {menu_id}")
        return menu_id
    else:
        _delete_rich_menu(menu_id)
        return None


def setup_member_rich_menu():
    """Create and store the Member Rich Menu (if not already existing)"""
    existing_id = _get_stored_menu_id("member")
    
    # Verify existing menu is still valid on LINE's side
    if existing_id:
        check = requests.get(
            f"{LINE_API_BASE}/richmenu/{existing_id}",
            headers=HEADERS
        )
        if check.status_code == 200:
            print("✅ Member Rich Menu already exists, skipping creation.")
            return existing_id
        else:
            print("⚠️ Stored Member Rich Menu ID is stale, recreating...")
    
    menu_id = _create_rich_menu(MEMBER_RICH_MENU)
    if not menu_id:
        return None
    
    if _upload_rich_menu_image(menu_id, MEMBER_MENU_IMAGE):
        _store_menu_id("member", menu_id)
        print(f"✅ Member Rich Menu created: {menu_id}")
        return menu_id
    else:
        _delete_rich_menu(menu_id)
        return None


def setup_admin_rich_menu():
    """Create and store the Admin Rich Menu (if not already existing)"""
    existing_id = _get_stored_menu_id("admin")
    
    if existing_id:
        check = requests.get(
            f"{LINE_API_BASE}/richmenu/{existing_id}",
            headers=HEADERS
        )
        if check.status_code == 200:
            print("✅ Admin Rich Menu already exists, skipping creation.")
            return existing_id
        else:
            print("⚠️ Stored Admin Rich Menu ID is stale, recreating...")
    
    menu_id = _create_rich_menu(ADMIN_RICH_MENU)
    if not menu_id:
        return None
    
    if _upload_rich_menu_image(menu_id, ADMIN_MENU_IMAGE):
        _store_menu_id("admin", menu_id)
        print(f"✅ Admin Rich Menu created: {menu_id}")
        return menu_id
    else:
        _delete_rich_menu(menu_id)
        return None


def link_member_menu(user_id):
    """Link the member Rich Menu to a specific user"""
    menu_id = _get_stored_menu_id("member")
    if not menu_id:
        menu_id = setup_member_rich_menu()
    if menu_id:
        return _link_rich_menu_to_user(user_id, menu_id)
    return False


def link_admin_menu():
    """Link the admin Rich Menu to the admin user"""
    if not Config.ADMIN_USER_ID:
        print("⚠️ ADMIN_USER_ID not set, skipping admin rich menu link.")
        return False
    
    menu_id = _get_stored_menu_id("admin")
    if not menu_id:
        menu_id = setup_admin_rich_menu()
    if menu_id:
        return _link_rich_menu_to_user(Config.ADMIN_USER_ID, menu_id)
    return False


def force_recreate_all():
    """
    Force recreate all Rich Menus (deletes old ones first).
    Use this when menu layout or image changes.
    """
    for role in ["default", "member", "admin"]:
        old_id = _get_stored_menu_id(role)
        if old_id:
            _delete_rich_menu(old_id)
            rich_menu_col.delete_one({"role": role})
            print(f"🗑️ Deleted old {role} Rich Menu: {old_id}")

    setup_default_rich_menu()
    setup_member_rich_menu()
    setup_admin_rich_menu()
    link_admin_menu()
    
    # Re-link the new member menu to all existing registered users
    try:
        from app.setup.database import get_all_registered_users
        members = get_all_registered_users()
        for member in members:
            user_id = member.get("user_id")
            if user_id and user_id != Config.ADMIN_USER_ID:
                link_member_menu(user_id)
        print(f"✅ Re-linked member menu to {len(members)} users.")
    except Exception as e:
        print(f"⚠️ Error re-linking member menus: {e}")

    print("✅ All Rich Menus recreated.")


# Bump this version when Rich Menu layout/areas/images change.
# On startup, if the stored version doesn't match, menus are force-recreated.
RICH_MENU_VERSION = "14"


def initialize_rich_menus():
    """
    Initialize all Rich Menus on app startup.
    - Auto-recreates if RICH_MENU_VERSION changed (layout update)
    - Creates menus if they don't exist
    - Links admin menu to admin user
    - Member menus are linked on registration/follow
    """
    print("🔧 Initializing Rich Menus...")

    # Check if version changed → force recreate
    version_doc = rich_menu_col.find_one({"role": "_version"})
    stored_version = version_doc.get("version") if version_doc else None

    if stored_version != RICH_MENU_VERSION:
        print(f"⚠️ Rich Menu version changed ({stored_version} → {RICH_MENU_VERSION}), recreating...")
        force_recreate_all()
        rich_menu_col.update_one(
            {"role": "_version"},
            {"$set": {"version": RICH_MENU_VERSION}},
            upsert=True
        )
    else:
        setup_default_rich_menu()
        setup_member_rich_menu()
        setup_admin_rich_menu()
        link_admin_menu()
    
    print("🔧 Rich Menu initialization complete.")
