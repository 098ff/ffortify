# 🤖 ffortify (N'foii Bot) - LINE Payment Management Bot

**N'foii (น้องฝอย)** is a LINE Chatbot developed using Python (FastAPI) designed to streamline membership management, verify payment slips, and automatically calculate next payment due dates.

## ✨ Key Features

### 📋 Core Features
* **📝 User Registration:** Collects user details (Name, Nickname, Tel, Email) and stores them in MongoDB.
* **💸 Payment Submission:** Handles payment slip images and parsing transaction details via Rich Menu + text commands (`#โอน`).
* **👮‍♂️ Admin Dashboard:** Sends Flex Messages to the admin for approval:
    * **Approve:** Records the transaction and notifies the user immediately.
    * **Reject:** Declines invalid transactions.
* **📅 Smart Due Date Calculation:** Automatically calculates the next billing cycle based on the user's input (supports Thai month names).
* **🧹 Auto Cleanup:** Automatically removes temporary slip images from the database if the user doesn't complete the submission within a set time (powered by APScheduler).

### 🎛️ Rich Menu — Member (3 buttons)
* **📋 ดูรายการ** — View personal transaction history separated by paid and pending status, including overdue detection.
* **💸 ส่งสลิป** — Start payment flow (send slip image → type `#โอน` with details).
* **❓ คำสั่ง** — View all available commands with descriptions.

### 🔧 Rich Menu — Admin (4 buttons, 2×2 grid)
* **📊 สถานะสมาชิก** — View all member statuses with latest paid date and overdue alerts.
* **🗑️ ลบประวัติ** — Delete member transaction history with double confirmation:
    * **Soft Delete** — Mark as deleted (recoverable).
    * **Hard Delete** — Permanently remove from MongoDB (irreversible).
* **🖼️ ดูสลิป** — View a specific transaction's slip image by providing member name, month, and year.
* **❓ คำสั่ง** — View all available admin commands with descriptions.

### 👥 Admin Text Commands
* `#members` — List all registered members.
* `#check [nickname]` — Check a specific member's payment status.
* `#ดูสลิป [nickname] [month] [year]` — View transaction slip image (e.g., `#ดูสลิป ฝ้าย ม.ค. 68`).
* `#ลบประวัติ [nickname]` — Delete member transaction history with confirmation.
* `MyID` — Get the admin's LINE User ID.
* `MyGroup` — Get the Group ID (for group chat setup).

### 🚫 No Duplicate Functions
All user-facing features are accessed **exclusively via Rich Menu buttons**. There are no duplicate text triggers (e.g., no "เช็คยอด" or "จ่ายเงิน" text commands). This ensures a clear, consistent UX where:
* **Rich Menu** = the single entry point for all member and admin features.
* **Text commands** only remain for: registration (`#regis`), slip details (`#โอน`), and admin-specific commands prompted by Rich Menu.

## 🔒 Security & Data Privacy

* **Role-based Access Control:** Admin commands are gated behind `ADMIN_USER_ID` check. Members cannot access admin features.
* **Data Isolation:** Members can only view their own transactions. No cross-user data leakage.
* **Delete Confirmation:** All delete operations require double confirmation (choose delete type → confirm) to prevent accidental data loss.
* **Soft Delete Support:** Deleted data can be recovered if soft-deleted, preserving data integrity.
* **LINE User ID never exposed:** Internal user IDs are never shown to users — only names and nicknames are displayed.
* **Rich Menu Separation:** Different Rich Menu layouts are linked to admin vs member users.

## 🛠️ Tech Stack

* **Language:** Python
* **Framework:** FastAPI
* **Database:** MongoDB (PyMongo)
* **Messaging API:** LINE Bot SDK
* **Deployment:** Render (Web Service)
* **Server:** Uvicorn (ASGI server)
* **Scheduler:** APScheduler

---

## ⚙️ Local Development Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/098ff/ffortify.git
    cd ffortify
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory and add the following:
    ```env
    PORT=8000
    CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
    CHANNEL_SECRET=your_line_channel_secret
    MONGO_URI=your_mongodb_connection_string
    BASE_URL=https://your-domain.com
    ADMIN_USER_ID=your_line_user_id
    GROUP_ID_TO_ALERT=your_group_id
    LINE_BOT_BASIC_ID=@your_bot_basic_id
    SLIP_TIMEOUT_HOURS=1
    ```

5.  **Prepare Rich Menu Images**
    Ensure the `assets/` directory contains:
    * `member_rich_menu.png` (2500×843px, 3 zones)
    * `admin_rich_menu.png` (2500×1686px, 4 zones in 2×2 grid)

6.  **Run the Application**
    ```bash
    python run.py
    ```
    Or directly:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

7.  **Expose Localhost (Optional for Testing)**
    * Use **Ngrok**: `ngrok http 8000`
    * Update the Webhook URL in LINE Developers Console to the Ngrok URL (e.g., `https://xxxx.ngrok-free.app/callback`).

---

## 🚀 Deployment on Render.com

1.  Create a new **Web Service** on [Render](https://render.com).
2.  Connect your GitHub repository.
3.  **Settings:**
    * **Runtime:** Python 3
    * **Build Command:** `pip install -r requirements.txt`
    * **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4.  **Environment Variables:** Add all variables from your `.env` file to Render's "Environment" tab.
5.  **Webhook:** Once deployed (Status: Live), copy the Render URL and update the Webhook URL in LINE Developers Console:
    * `https://ffortify.onrender.com/callback`

---

## 📂 Project Structure

```text
ffortify/
├── app/
│   ├── modules/
│   │   ├── handlers/            # Event Handlers
│   │   │   ├── __init__.py      # Handler exports
│   │   │   ├── follows.py       # Follow event (Friend add + Rich Menu link)
│   │   │   ├── messages.py      # Text/Image message logic (no duplicates with Rich Menu)
│   │   │   └── postbacks.py     # Postback actions (Rich Menu + approve/reject + help)
│   │   ├── line_api.py          # LINE Bot API Instance
│   │   ├── rich_menu.py         # Rich Menu creation, upload & linking
│   │   └── scheduler.py         # Job Scheduler (Auto cleanup + reminders)
│   ├── setup/                   # Configuration & DB
│   │   ├── config.py
│   │   └── database.py          # MongoDB operations (users, transactions, slips)
│   ├── ui/                      # UI Templates
│   │   └── flex_messages.py     # Flex Message & text builders (admin flex, status, delete confirm)
│   ├── utils/                   # Helper Functions
│   │   ├── const.py             # Thai month constants
│   │   ├── date_time.py         # Date/time utilities
│   │   └── validators.py        # Input validation
│   ├── main.py                  # Define FastAPI + startup (scheduler, rich menus)
│   └── routes.py                # FastAPI Routes (Webhook /callback, slip serving)
├── assets/                      # Static assets
│   ├── member_rich_menu.png     # Member Rich Menu image (2500×843, 3 zones)
│   └── admin_rich_menu.png      # Admin Rich Menu image (2500×1686, 4 zones)
├── .env                         # Environment Variables (Ignored)
├── .gitignore
├── requirements.txt             # Dependencies
└── run.py                       # Entry point (Local run)
```

---

## 📊 Database Schema (MongoDB)

### `users` collection
| Field | Type | Description |
|-------|------|-------------|
| `user_id` | string | LINE User ID |
| `first_name` | string | First name |
| `last_name` | string | Last name |
| `nickname` | string | Nickname (unique) |
| `tel_number` | string | Phone number |
| `email` | string | Email address |
| `is_registered` | boolean | Registration status |
| `next_due_date` | datetime | Next payment due date |
| `temp_slip_id` | string | Temporary slip file ID |

### `transactions` collection
| Field | Type | Description |
|-------|------|-------------|
| `_id` | string (UUID) | Transaction ID |
| `uid` | string | LINE User ID |
| `amount` | float | Transfer amount |
| `cnt_month` | int | Number of months paid |
| `billing` | string | Billing period text |
| `slip_id` | string | Reference to slip image |
| `status` | string | `pending` / `completed` / `rejected` |
| `is_deleted` | boolean | Soft delete flag |

### `slips` collection
| Field | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Auto-generated |
| `filename` | string | Original filename |
| `data` | Binary | Image binary data |

### `rich_menus` collection
| Field | Type | Description |
|-------|------|-------------|
| `role` | string | `member` / `admin` |
| `rich_menu_id` | string | LINE Rich Menu ID |
