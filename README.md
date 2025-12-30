# 🤖 ffortify (N'foii Bot) - LINE Payment Management Bot

**N'foii (น้องฝอย)** is a LINE Chatbot developed using Python (Flask) designed to streamline membership management, verify payment slips, and automatically calculate next payment due dates.

## ✨ Key Features

* **📝 User Registration:** Collects user details (Name, Nickname, Tel, Email) and stores them in MongoDB.
* **💸 Payment Submission:** Handles payment slip images and parsing transaction details via text commands (`#โอน`).
* **👮‍♂️ Admin Dashboard:** Sends Flex Messages to the admin for approval:
    * **Approve:** Records the transaction and notifies the user immediately.
    * **Reject:** Declines invalid transactions.
* **📅 Smart Due Date Calculation:** Automatically calculates the next billing cycle based on the user's input (supports Thai month names).
* **🔍 Status Check:** Users can check their own payment status and next due date (`เช็คยอด`).
* **🧹 Auto Cleanup:** Automatically removes temporary slip images from the database if the user doesn't complete the submission within a set time (powered by APScheduler).

## 🛠️ Tech Stack

* **Language:** Python 3.13
* **Framework:** Flask
* **Database:** MongoDB (PyMongo)
* **Messaging API:** LINE Bot SDK
* **Deployment:** Render (Web Service)
* **Server:** Gunicorn
* **Scheduler:** APScheduler

---

## ⚙️ Local Development Setup

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/098ff/ffortify.git](https://github.com/098ff/ffortify.git)
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
    CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
    CHANNEL_SECRET=your_line_channel_secret
    MONGO_URI=your_mongodb_connection_string
    ADMIN_USER_ID=your_line_user_id
    SLIP_TIMEOUT_HOURS=3
    TZ=Asia/Bangkok
    ```

5.  **Run the Application**
    ```bash
    flask run -p 8000
    ```

6.  **Expose Localhost (Optional for Testing)**
    * Use **Ngrok**: `ngrok http 8000`
    * Update the Webhook URL in LINE Developers Console to the Ngrok URL (e.g., `https://xxxx.ngrok-free.app/callback`).

---

## 🚀 Deployment on Render.com

1.  Create a new **Web Service** on [Render](https://render.com).
2.  Connect your GitHub repository.
3.  **Settings:**
    * **Runtime:** Python 3
    * **Build Command:** `pip install -r requirements.txt`
    * **Start Command:** `gunicorn --bind 0.0.0.0:$PORT app:app`
4.  **Environment Variables:** Add all variables from your `.env` file to Render's "Environment" tab.
5.  **Webhook:** Once deployed (Status: Live), copy the Render URL and update the Webhook URL in LINE Developers Console:
    * `https://your-app-name.onrender.com/callback`

---

## 📂 Project Structure

```text
ffortify/
├── app/
│   ├── modules/
│   │   ├── handlers/        # Event Handlers
│   │   │   ├── follows.py   # Follow event (Friend add)
│   │   │   ├── messages.py  # Text/Image message logic
│   │   │   └── postbacks.py # Button click actions
│   │   ├── line_api.py      # LINE Bot API Instance
│   │   └── scheduler.py     # Job Scheduler (Auto cleanup)
│   ├── setup/               # Configuration & DB
│   │   ├── config.py
│   │   └── database.py
│   ├── ui/                  # UI Templates
│   │   └── flex_messages.py
│   ├── utils/               # Helper Functions
│   │   ├── const.py
│   │   ├── date_time.py
│   │   └── validators.py
│   ├── __init__.py          # Flask App Factory
│   └── routes.py            # Webhook Endpoint (/callback)
├── .env                     # Environment Variables (Ignored)
├── .gitignore
├── requirements.txt         # Dependencies
└── run.py                   # Entry point (Local run)
