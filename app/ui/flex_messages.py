from app.setup.config import Config

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


def create_members_list_text(members):
    """สร้างข้อความแสดงรายชื่อสมาชิกทั้งหมด"""
    if not members:
        return "📋 ยังไม่มีสมาชิกลงทะเบียน"

    lines = [f"📋 รายชื่อสมาชิกทั้งหมด ({len(members)} คน)\n"]
    for i, m in enumerate(members, 1):
        nickname = m.get("nickname", "ไม่ทราบ")
        first_name = m.get("first_name", "")
        last_name = m.get("last_name", "")
        email = m.get("email", "-")
        lines.append(f"{i}. {first_name} {last_name} ({nickname})")
        lines.append(f"   📧 {email}")

    return "\n".join(lines)


def create_user_transactions_text(transactions, user_nickname):
    """
    สร้างข้อความแสดงรายการ Transaction ของ User
    แยก: ✅ จ่ายแล้ว vs ❌ ค้างชำระ/เลยกำหนด
    """
    from datetime import datetime

    if not transactions:
        return f"📋 พี่{user_nickname}ยังไม่มีรายการชำระเงินค่ะ"

    paid = []
    pending = []

    for tx in transactions:
        status = tx.get("status")
        billing = tx.get("billing", "-")
        amount = tx.get("amount", 0)
        months = tx.get("cnt_month", 0)
        display_amount = f"{amount:g}" if isinstance(amount, float) else str(amount)

        entry = f"  💰 ฿{display_amount} ({months} เดือน) - {billing}"

        if status == "completed":
            paid.append(entry)
        elif status == "rejected":
            continue  # ไม่แสดงรายการถูกปฏิเสธ
        else:  # pending
            pending.append(entry)

    lines = [f"📋 รายการของพี่{user_nickname}\n"]

    if paid:
        lines.append("✅ จ่ายแล้ว:")
        lines.extend(paid)

    if pending:
        lines.append("\n⏳ รอตรวจสอบ:")
        lines.extend(pending)

    if not paid and not pending:
        lines.append("ยังไม่มีรายการที่ผ่านการอนุมัติค่ะ")

    return "\n".join(lines)


def create_admin_status_text(member_statuses):
    """
    สร้างข้อความสถานะสมาชิกทั้งหมดสำหรับ Admin
    แสดง: ชื่อ, จ่ายล่าสุดวันไหน, ค้างชำระไหม
    """
    from app.utils.date_time import get_thai_month_year

    if not member_statuses:
        return "📊 ยังไม่มีข้อมูลสมาชิก"

    lines = [f"📊 สถานะสมาชิกทั้งหมด ({len(member_statuses)} คน)\n"]

    overdue_list = []
    normal_list = []

    for m in member_statuses:
        nickname = m.get("nickname", "ไม่ทราบ")
        first_name = m.get("first_name", "")
        last_paid = m.get("last_paid_date")
        next_due = m.get("next_due_date")
        is_overdue = m.get("is_overdue", False)

        last_paid_str = last_paid.strftime("%d/%m/%Y") if last_paid else "ยังไม่เคยจ่าย"
        next_due_str = get_thai_month_year(next_due) if next_due else "ยังไม่มีข้อมูล"

        entry = f"👤 {first_name} ({nickname})\n   💵 จ่ายล่าสุด: {last_paid_str}\n   📅 บิลถัดไป: 13 {next_due_str}"

        if is_overdue:
            entry += "\n   🔴 ค้างชำระ!"
            overdue_list.append(entry)
        else:
            entry += "\n   🟢 ปกติ"
            normal_list.append(entry)

    if overdue_list:
        lines.append("⚠️ ค้างชำระ:")
        lines.extend(overdue_list)
        lines.append("")

    if normal_list:
        lines.append("✅ ปกติ:")
        lines.extend(normal_list)

    return "\n".join(lines)


def create_delete_confirm_flex(nickname, user_id):
    """สร้าง Flex Message ยืนยันการลบข้อมูล"""
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "⚠️ ยืนยันการลบข้อมูล",
                    "weight": "bold",
                    "color": "#E53E3E",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": f"ต้องการลบประวัติของ '{nickname}' ใช่หรือไม่?",
                    "wrap": True,
                    "margin": "md",
                    "size": "sm",
                    "color": "#555555"
                },
                {
                    "type": "separator",
                    "margin": "xl"
                },
                {
                    "type": "text",
                    "text": "เลือกวิธีลบ:",
                    "weight": "bold",
                    "margin": "xl",
                    "size": "sm"
                },
                {
                    "type": "text",
                    "text": "• Soft Delete = ซ่อนข้อมูล (กู้คืนได้)\n• Hard Delete = ลบถาวร (กู้คืนไม่ได้!)",
                    "wrap": True,
                    "margin": "sm",
                    "size": "xs",
                    "color": "#888888"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#F6AD55",
                    "action": {
                        "type": "postback",
                        "label": "🗂️ Soft Delete (ซ่อน)",
                        "data": f"action=confirm_soft_delete&target_uid={user_id}"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#E53E3E",
                    "action": {
                        "type": "postback",
                        "label": "🗑️ Hard Delete (ลบถาวร)",
                        "data": f"action=confirm_hard_delete&target_uid={user_id}"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "postback",
                        "label": "❌ ยกเลิก",
                        "data": "action=cancel_delete"
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