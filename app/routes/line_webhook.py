from fastapi import APIRouter, Request, HTTPException
from linebot.exceptions import InvalidSignatureError
from app.services.linebot.event_services import handler
from app.models.text2emoji import text_to_emoji

line_router = APIRouter(prefix="/line")
print("line_webhook")


@line_router.post("/webhook")
async def callback(request: Request) -> str:
    # image = await inference_model()
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=400, detail="X-Line-Signature header missing")
    text_to_emoji("A <s0><s1> pig look like kobe")
    body = await request.body()  # body 回傳 bytes 形式
    try:
        print(f"{body.decode('utf-8')=}")
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Missing Parameter")
    return "OK"
