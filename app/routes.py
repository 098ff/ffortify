from flask import Blueprint, request, abort, send_file
from linebot.exceptions import InvalidSignatureError
from app.modules.line_api import handler
from app.setup.database import get_slip_image
import io
# Import handlers เพื่อให้ decorator ทำงาน
import app.modules.handlers 

bp = Blueprint('main', __name__)

@bp.route("/slip/<file_id>")
def serve_slip(file_id):
    # ดึงข้อมูลจาก MongoDB
    file_doc = get_slip_image(file_id)
    
    if not file_doc:
        return "Image not found", 404
        
    # แปลง Binary กลับเป็นรูปภาพแล้วส่งออกไป
    return send_file(
        io.BytesIO(file_doc['data']),
        mimetype='image/jpeg',
        as_attachment=False,
        download_name=file_doc['filename']
    )

@bp.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@bp.route("/")
def home():
    return "Spotify Bot Modular Version is Running!"