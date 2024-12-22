import json

# line tools
from linebot.v3 import WebhookHandler
from linebot.v3.webhooks import (
    MessageEvent, 
    TextMessageContent,
    PostbackEvent,
    ImageMessageContent, 
    StickerMessageContent,
)

# custom tools
from app.config import LineBot
import inspect
from app.utils.logger import linebot_logger
from app.services.linebot.msg_services import (
    NonePeriod,
    PhotoCaptioningPeriod,
    UserActioningPeriod,
    CaptionModifyingPeriod,
    StoryGeneratingPeriod,
    StoryPreviewPeriod,
    StoryModifyingPeriod,
    AudioGeneratingPeriod,
    Action,
    Status,
    User,
)

class AsyncWebhookHandler(WebhookHandler):
    """Async Webhook Handler."""

    async def handle(self, body, signature):
        """Handle webhook asynchronously.

        :param str body: Webhook request body (as text)
        :param str signature: X-Line-Signature value (as text)
        """
        payload = self.parser.parse(body, signature, as_payload=True)

        for event in payload.events:
            func = None
            key = None

            if isinstance(event, MessageEvent):
                key = self._WebhookHandler__get_handler_key(
                    event.__class__, event.message.__class__)
                func = self._handlers.get(key, None)

            if func is None:
                key = self._WebhookHandler__get_handler_key(event.__class__)
                func = self._handlers.get(key, None)

            if func is None:
                func = self._default

            if func is None:
                linebot_logger.info('No handler for ' + key + ' and no default handler')
            else:
                await self.__invoke_func(func, event, payload)

    @classmethod
    async def __invoke_func(cls, func, event, payload):
        """Invoke the given function asynchronously if necessary."""
        if inspect.iscoroutinefunction(func):
            (has_varargs, args_count) = cls.__get_args_count(func)
            if has_varargs or args_count == 2:
                await func(event, payload.destination)
            elif args_count == 1:
                await func(event)
            else:
                await func()
        else:
            super(AsyncWebhookHandler, cls)._WebhookHandler__invoke_func(func, event, payload)

    @staticmethod
    def __get_args_count(func):
        """Get the argument count of a function."""
        arg_spec = inspect.getfullargspec(func)
        return (arg_spec.varargs is not None, len(arg_spec.args))

async_handler = AsyncWebhookHandler(LineBot.channel_secret)

# 文字訊息
@async_handler.add(event=MessageEvent, message=TextMessageContent)
async def text_message_event(event):
    # 准許的狀態：modifying
    linebot_logger.info(f"[Text] {event}")
    
    user = User(event.source.user_id)
    
    # 用戶打斷，回應打斷訊息
    if user.current_status == Status.NONE:
        state_service = NonePeriod(event)
        await state_service.handle_interrupt_message(user)
    elif user.current_status == Status.PHOTO_CAPTIONING:
        state_service = PhotoCaptioningPeriod(event)
        await state_service.handle_interrupt_message(user, "Text Message")
    elif user.current_status == Status.USER_ACTIONING:
        state_service = UserActioningPeriod(event)
        await state_service.resend_menu_select_message(user)
    elif user.current_status == Status.STORY_GENERATING:
        state_service = StoryGeneratingPeriod(event)
        await state_service.handle_interrupt_message(user, "Text Message")
    elif user.current_status == Status.STORY_PREVIEW:
        state_service = StoryPreviewPeriod(event)
        await state_service.resend_menu_select_message(user)
    elif user.current_status == Status.AUDIO_GENERATING:
        # 回應貼圖，儘快完成語音製作
        action_service = AudioGeneratingPeriod(event)
        await action_service.send_waiting_sticker(user)
    
    # 准許回應，須對内容處理
    elif user.current_status == Status.CAPTION_MODIFYING:
        action_service = CaptionModifyingPeriod(event)
        await action_service.update_photo_caption_by_user(user)
    elif user.current_status == Status.STORY_MODIFYING:
        action_service = StoryModifyingPeriod(event)
        await action_service.update_story_by_user(user)
    elif user.current_status == Status.STORY_USER_PRODUCING:
        action_service = StoryModifyingPeriod(event)
        await action_service.append_story_by_user(user)



# 貼圖訊息
@async_handler.add(event=MessageEvent, message=StickerMessageContent)
async def sticker_msg_event(event):
    user = User(event.source.user_id)
    linebot_logger.info(f"[Sticker] {event}")
    linebot_logger.info(f"[Sticker] {user.__dict__=}")

    # 用戶傳貼圖打斷，回應打斷訊息
    if user.current_status == Status.NONE:
        state_service = NonePeriod(event)
        await state_service.handle_interrupt_message(user)
    elif user.current_status == Status.PHOTO_CAPTIONING:
        state_service = PhotoCaptioningPeriod(event)
        await state_service.handle_interrupt_message(user, "Text Message")
    elif user.current_status == Status.USER_ACTIONING:
        state_service = UserActioningPeriod(event)
        await state_service.resend_menu_select_message(user)
    elif user.current_status == Status.STORY_GENERATING:
        state_service = StoryGeneratingPeriod(event)
        await state_service.handle_interrupt_message(user, "Text Message")
    elif user.current_status == Status.STORY_PREVIEW:
        state_service = StoryPreviewPeriod(event)
        await state_service.resend_menu_select_message(user)
    elif user.current_status == Status.AUDIO_GENERATING:
        action_service = AudioGeneratingPeriod(event)
        await action_service.send_waiting_sticker(user)
    elif user.current_status == Status.CAPTION_MODIFYING:
        action_service = CaptionModifyingPeriod(event)
        await action_service.update_photo_caption_by_user(user)

    elif user.current_status == Status.STORY_MODIFYING:
        action_service = StoryModifyingPeriod(event)
        await action_service.update_story_by_user(user)
    elif user.current_status == Status.STORY_USER_PRODUCING:
        action_service = StoryModifyingPeriod(event)
        await action_service.append_story_by_user(user)


# 照片訊息
@async_handler.add(event=MessageEvent, message=ImageMessageContent)
async def img_msg_event(event): 
    # 准許的狀態：None
    user = User(event.source.user_id)
    linebot_logger.info(f"[Image] {event}")
    linebot_logger.info(f"[Image] {user.__dict__=}")

    if user.current_status == Status.NONE:
        # 模型推理圖片内容，推理完會推送結果和選單
        action_service = PhotoCaptioningPeriod(event)
        await action_service.photo_captioning(user)
        
    elif user.current_status == Status.PHOTO_CAPTIONING:
        action_service = PhotoCaptioningPeriod(event)
        await action_service.handle_interrupt_message(user, "Image Message")
    
    elif user.current_status == Status.USER_ACTIONING:
        action_service = UserActioningPeriod(event)
        await action_service.resend_menu_select_message(user)

    elif user.current_status == Status.STORY_GENERATING:
        state_service = StoryGeneratingPeriod(event)
        await state_service.handle_interrupt_message(event, "Image Message")
    
    elif user.current_status == Status.STORY_PREVIEW:
        state_service = StoryPreviewPeriod(event)
        await state_service.resend_menu_select_message(user)
    
    # 生成音檔狀態為低調背景執行，用戶會以爲在 NONE 狀態，所以可以偷偷回應等我一下貼圖 
    elif user.current_status == Status.AUDIO_GENERATING:
        action_service = AudioGeneratingPeriod(event)
        await action_service.send_waiting_sticker(user)
    
    elif user.current_status in (Status.STORY_MODIFYING, Status.STORY_USER_PRODUCING, Status.CAPTION_MODIFYING):
        pass


    
# 回應訊息
@async_handler.add(event=PostbackEvent)
async def postback_event(event):

    user = User(event.source.user_id)
    data_dict = json.loads(event.postback.data)
    action = Action(data_dict.get("action"))
    type = data_dict.get("type")
    message = data_dict.get("message")

    linebot_logger.info(f"[Postback] {data_dict}")
    linebot_logger.info(f"[Postback] {user.__dict__=}")

    if user.current_status == Status.USER_ACTIONING:
        # 條件根據 quick reply 裏 data 的 action
        if action == Action.TYPE_COMFIRM:
            state_service = StoryGeneratingPeriod(event)
            await state_service.handle_generating_story(user, type, message) # 回傳story同時有附上功能選單(會判斷是否有延申功能)

        elif action == Action.MODIFY_REQUEST:
            action_service = CaptionModifyingPeriod(event)
            await action_service.inform_modifying_start(user)

        elif action == Action.STORY_CLOSED:
            state_service = AudioGeneratingPeriod(event)
            await state_service.generating_audio(user)
            
    elif user.current_status == Status.STORY_PREVIEW:
        if action == Action.STORY_EXTEND:
            action_service = StoryGeneratingPeriod(event)
            await action_service.handle_generating_story(user, type)
        
        elif action == Action.MODIFY_REQUEST:
            action_service = StoryModifyingPeriod(event)
            await action_service.inform_modifying_start(user)
        
        elif action == Action.USER_PRODUCE_REQUEST:
            action_service = StoryModifyingPeriod(event)
            await action_service.inform_produce_start(user)
        
        elif action == Action.STORY_CLOSED:
            action_service = AudioGeneratingPeriod(event)
            await action_service.generating_audio(user)

        
    