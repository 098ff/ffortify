from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from linebot.exceptions import InvalidSignatureError
from app.modules.line_api import handler
from app.setup.database import get_slip_image
import io

# import handlers เพื่อให้ decorator ของ LINE ทำงาน
import app.modules.handlers

router = APIRouter()

@router.get("/slip/{file_id}")
async def serve_slip(file_id: str):
    file_doc = get_slip_image(file_id)

    if not file_doc:
        raise HTTPException(status_code=404, detail="Image not found")

    return StreamingResponse(
        io.BytesIO(file_doc["data"]),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f'inline; filename="{file_doc["filename"]}"'
        }
    )

@router.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    body = await request.body()
    body_text = body.decode("utf-8")

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

@router.get("/")
async def home():
    return "Spotify Bot Modular Version is Running!"