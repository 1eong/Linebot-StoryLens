from app.config import LineBot
from linebot import LineBotApi, WebhookHandler
from linebot.models.events import *
from linebot.models.send_messages import TextSendMessage
from app.utils.image_utils import ImageHelper
from app.utils.utils import PathTool

line_reply_api = LineBotApi(LineBot.channel_access_token)
handler = WebhookHandler(LineBot.channel_secret)


@handler.add(event=FollowEvent)
def follow_event(event):
    pass


@handler.add(event=UnfollowEvent)
def unfollow_event(event):
    pass


@handler.add(event=MessageEvent)
def message_event(event):
    print("message_event")
    print(f"{handler=}")
    pass


@handler.add(event=MessageEvent, message=(TextMessage))
def text_message_event(event):
    print("text_message_event")
    print(f"{handler=}")
    pass  # 回覆用戶傳來的文字訊息
    # line_reply_api.reply_message(
    #     event.reply_token, TextSendMessage(text=f"你說的是: {event.message.text}")
    # )


@handler.add(event=MessageEvent, message=(ImageMessage))
def img_msg_event(event):
    msg_id = event.message.id
    message_content = line_reply_api.get_message_content(msg_id)

    print(f"{type(message_content)=}")
    print(message_content)
    ImageHelper.download_binary_stream(
        message_content, PathTool.join_path("app/downloads", "image.jpg")
    )
    pass
