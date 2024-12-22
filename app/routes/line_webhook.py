import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from linebot.v3.exceptions import InvalidSignatureError
from app.services.linebot.event_services import async_handler
from app.utils.utils import PathTool
from app.utils.logger import linebot_logger

line_router = APIRouter(prefix="/line")

line_router.mount("/static", StaticFiles(directory="app/static"), name="static")

@line_router.post("/webhook")
async def callback(request: Request) -> str:
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=400, detail="X-Line-Signature header missing")

    body = await request.body()  # body 回傳 bytes 形式
    body = body.decode("utf-8")
    
    try:
        await async_handler.handle(body, signature)

    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "OK"

@line_router.get("/static/audio/{audio_name}")
async def get_audio_url(audio_name: str):
    file_path = PathTool.join_path("app","static","audio", audio_name)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    linebot_logger.warning(f"Audio file not found:{file_path}")
    return {"error": "File not found"}
