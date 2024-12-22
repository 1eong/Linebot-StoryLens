import asyncio
import json
import random
from typing import TypedDict, Union
from PIL import Image
from enum import Enum
from pathlib import Path

# self package
from app.utils.image_utils import ImageHelper
from app.utils.utils import PathTool, JsonTool
from app.utils.logger import linebot_logger
from app.config import EnvConfig, LineBot

# model module
from app.models.text_generation import mandrine_llm
from app.models.text_to_speech import speech
from app.models.image_to_text import image2text
from app.models.translator import translator

# line module
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    ApiClient,
    AsyncMessagingApi,
    MessagingApi,
    AsyncMessagingApiBlob,
    QuickReply,
    QuickReplyItem,
    PostbackAction, 
    ReplyMessageRequest, 
    PushMessageRequest,
    TextMessage,
    AudioMessage,
    StickerMessage
)
from linebot.v3.webhooks import (
    ImageMessageContent,
)

configuration = Configuration(access_token=LineBot.channel_access_token)
async_api_client = AsyncApiClient(configuration)
async_line_bot_api = AsyncMessagingApi(async_api_client)
async_messaging_api = AsyncMessagingApiBlob(async_api_client)

class QuickReplyDict(TypedDict):
    label: str
    display_text: str
    data: dict

def quick_reply(qr_list: list[QuickReplyDict]) -> QuickReply:
    """
    dict 形態包裝成 quickReply物件形態
    """
    template = QuickReply(
                    items=[
                        QuickReplyItem(
                            action=PostbackAction(
                                label=qr_item.get("label"),
                                data=json.dumps(qr_item.get("data"), ensure_ascii=False),
                                display_text=qr_item.get("display_text")
                            ),
                            image_url=None
                        ) 
                        for qr_item in qr_list
                    ]
                )
    linebot_logger.info(f"[function] quick_reply: {template=}")
    return template

# 以 server 視角去判斷 action
class Action(Enum):
    PHOTO_RECEIVED = "photo_received"
    GENERATED = "generated"
    TYPE_COMFIRM = "type_confirm"
    MODIFY_REQUEST = "modify_request"
    MODIFYED = "modifyed"
    USER_PRODUCE_REQUEST = "user_produce_request"
    USER_PRODUCED = "user_produced"
    STORY_EXTEND = "story_extend"
    STORY_CLOSED = "story_closed"
    
class Status(Enum):
    NONE = "state_none" # 告訴使用者 發照片
    PHOTO_CAPTIONING = "state_photo_captioning" # 回應 正在理解照片内容
    CAPTION_MODIFYING = "state_caption_modfying" # 接受各種text，作爲
    USER_ACTIONING = "state_user_actioning" # 中斷需重發 quick reply 處理
    STORY_GENERATING = "state_story_generating" # 回應 正在生成故事
    STORY_PREVIEW = "state_story_preview" # 中斷 需重發 quick reply 處理
    STORY_MODIFYING = "state_story_modifying" # 任何内容都行，使用者輸入即爲内容
    STORY_USER_PRODUCING = "state_story_user_producing"
    AUDIO_GENERATING = "state_audio_generating" 

class User:
    """
    讀取 user 的 json 檔案，並記錄當前狀態。
    
    可對照 user_states_schema.json
    {
        "user_id": "xxxx",
        "user_name: "Daniel ..."
        "status": "state_none"
        ...
    }
    """
    def __init__(self, id: int):
        self.id = id
        self.name = self.__get_user_name()
        json_schema_path = Path.cwd() / "app" / "schemas" / "user_states_schema.json"
        data_path = Path.cwd() / "app" / "data" / f"user_state_{id}.json"
        self.user_file_tool = JsonTool(data_path, json_schema_path)
        self.data_dict = self.__get_data_dict()
        
        # 記錄該 user 對應的 server 狀態
        self.current_status: Status = self.__get_status(self.data_dict)
        self.image_caption: str = self.data_dict.get("image_caption")
        self.story_type: str = self.data_dict.get("story_type")
        self.story_list: list = self.data_dict.get("story_list", [])
        self.story_size: int = len(self.story_list) if self.story_list else 0

    def __get_user_name(self):
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            name = line_bot_api.get_profile(self.id).display_name
            return name

    def __get_data_dict(self) -> dict:
        try:
            data_dict = self.user_file_tool.read_file()
        except FileNotFoundError:
            data_dict = self.__create_user_file()
        return data_dict
    
    def __get_status(self, data_dict: dict) -> Status:
        # status 驗證
        status_value = data_dict.get("status")
        if status_value in Status._value2member_map_:
            return Status(status_value)
        linebot_logger.warning(f"Invalid status value for user {self.id}, defaulting to NONE.")
        return Status.NONE

    def save_story_type(self, story_type: str):
        self.story_type = story_type
        self.data_dict["story_type"] = story_type
    
    def update_story_list(self, input: str):
        """更新最後一個story内容"""
        if not self.story_list:
            raise "story list 目前爲空，無法替你更新。"
        self.story_list[-1] = input
        self.data_dict["story_list"] = self.story_list

    def append_story_list(self, input: str):
        self.story_list.append(input)
        self.story_size = len(self.story_list)
        self.data_dict["story_list"] = self.story_list
    
    def update_photo_caption(self, image_caption: str):
        self.image_caption = image_caption
        self.data_dict["image_caption"] = image_caption
        self.user_file_tool.write_file(self.data_dict)
    
    def clear_user_file(self):
        self.__create_user_file()

    def update_state(self, action: Action):
        """
        根據當前動作更新狀態

        action：當前狀態
        """
        if self.data_dict:
            new_state = self.__change_state(action)
            self.current_status = new_state
            self.data_dict["status"] = new_state.value
            self.user_file_tool.write_file(self.data_dict)
            return True
        linebot_logger.warning(f"Invalid user data_dict: {self.data_dict}")
        return False
    
    def __create_user_file(self):
        data_dict = {"user_id": self.id, "user_name": self.name,"status": Status.NONE.value}
        self.user_file_tool.write_file(data_dict)
        return data_dict

    def __change_state(self, action: Action) -> Status:
        if self.current_status == Status.NONE:
            if action == Action.PHOTO_RECEIVED: # 用戶觸發
                return Status.PHOTO_CAPTIONING
        
        if self.current_status == Status.PHOTO_CAPTIONING:
            if action == Action.GENERATED: # 伺服器 觸發
                return Status.USER_ACTIONING
        
        if self.current_status == Status.CAPTION_MODIFYING:
            if action == Action.MODIFYED:    # 用戶觸發
                return Status.USER_ACTIONING
    
        if self.current_status == Status.USER_ACTIONING:
            if action == Action.TYPE_COMFIRM: # 用戶觸發
                return Status.STORY_GENERATING
            if action == Action.MODIFY_REQUEST: # 用戶觸發
                return Status.CAPTION_MODIFYING
            if action == Action.STORY_CLOSED: # 用戶觸發
                return Status.AUDIO_GENERATING
        
        if self.current_status == Status.STORY_GENERATING:
            if action == Action.GENERATED:
                return Status.STORY_PREVIEW
        
        if self.current_status == Status.STORY_PREVIEW:
            if action == Action.STORY_EXTEND: # 用戶觸發
                return Status.STORY_GENERATING
            if action == Action.USER_PRODUCE_REQUEST:
                return Status.STORY_USER_PRODUCING
            if action == Action.MODIFY_REQUEST: # 用戶觸發
                return Status.STORY_MODIFYING
            if action == Action.STORY_CLOSED: # 用戶觸發
                return Status.AUDIO_GENERATING
        
        if self.current_status == Status.STORY_MODIFYING:
            if action == Action.MODIFYED: # 用戶觸發
                return Status.STORY_PREVIEW
        
        if self.current_status == Status.STORY_USER_PRODUCING:
            if action == Action.USER_PRODUCED: # 用戶觸發
                return Status.STORY_PREVIEW
        
        if self.current_status == Status.AUDIO_GENERATING:
            if action == Action.GENERATED: # 伺服器觸發
                return Status.NONE
        linebot_logger.warning(f"status:{action.value} is not a valid action.")
        return self.current_status

"""
================================= type service ========================
"""
class TextMessageService:
    """
    回應的 Message 物件

    創建后會獲取定義在json的回應模板

    json_file: app/data/reply_message.json

    json_schema: app/data/reply_message_schema.json

    訊息類型：Text Message, Image Message

    方法1：從 “狀態” “訊息類型” 模板中條一則回復
    """
    def __init__(self):
        template_path = Path.cwd() / "app" / "data" / "reply_message.json"
        schema_path = Path.cwd() / "app" / "schemas" / "reply_message_schema.json"
        self.json_tool:JsonTool = JsonTool(template_path, schema_path)
        self.message_type_list = ["Text Message", "Image Message"]
        self.data_template = self.json_tool.read_file()

    def get_message_by_random(self, message_type: str, state: str) -> str:
        if message_type not in self.message_type_list:
            raise f"{message_type} 不是規範訊息類型。"
        
        if (msg_type_dict:= self.data_template.get(message_type)) is None:
            linebot_logger.warning(f"{self.template_path} 格式不符合預期，請確認。")
            return None
        
        # 有 key 且 不爲空 list
        if msg_state_list:= msg_type_dict.get(state):
            return random.choice(msg_state_list)
        
        return None

class QuickReplyMenu:
    def __init__(self):
        json_schema_path = Path.cwd() / "app" / "schemas" / "quick_reply.json"
        data_path = Path.cwd() / "app" / "data" / "quick_reply.json"
        self.json_tool = JsonTool(data_path, json_schema_path)
        self.template_dict: dict = self.__get_json_template()
        linebot_logger.info(f"[class] QuickReplyMenu: {self.template_dict=}")
    
    def __get_json_template(self):
        try:
            return self.json_tool.read_file()
        except FileNotFoundError as e:
            raise e

    def get_template(self, state: Status) -> list:
        linebot_logger.info(f"{state.value=}")
        if template:= self.template_dict.get(state.value):
            linebot_logger.info(f"{template=}")
            return template
        return []


class ImageMessageService:
    def __init__(self, user_id: str):
        self.image_path = PathTool.join_path("app", "downloads", f"image{user_id}.jpg")

    async def download_image(self, image_content: bytes):
        # 對二進制内容進行下載圖片
        await asyncio.to_thread(ImageHelper.download_binary_stream, image_content, self.image_path)


"""
=============================== status period ==============================
"""

class Period:

    def __init__(self, event):
        self.event = event

    async def handle_interrupt_message(self, user: User, msg_type: str = "Text Message"):
        """
        對於打擾訊息的回應

        Args:
            user (User): user物件
            msg_type (str): 收到的訊息類型（"TextMessage", "Image Message", "Sticker Message"）,使用前確保 reply_message.json 有創建回應列表
        """
        reply_service = TextMessageService()
        msg = reply_service.get_message_by_random("Text Message", user.current_status.value)
        response = await async_line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        replyToken=self.event.reply_token,
                        messages=[TextMessage(
                            text=msg)
                        ]
                    )
                )
        if response.status_code == 200:
            linebot_logger.info(f"[{user.current_status.value}] reply message send！\"{msg}\"")

class NonePeriod(Period):
    """
    預期：圖片訊息，其餘訊息皆爲打斷

    下一個狀態：解讀圖片（PhotoCaptioningPeriod）

    前一個狀態：生成語音（AudioGenerating）
    
    """
    pass
    async def handle_interrupt_message(self, user: User):
        linebot_logger.info(f"{self.event.message}=")
        reply_service = TextMessageService()
        if not isinstance(self.event.message, ImageMessageContent):
            response = await async_line_bot_api.reply_message_with_http_info(
                    ReplyMessageRequest(
                        replyToken=self.event.reply_token,
                        messages=[TextMessage(
                            text=reply_service.get_message_by_random("Text Message", user.current_status.value))
                        ]
                    )
                )
            if response.status_code == 200:
                linebot_logger.info(f"[{user.current_status}] interrupt_message send!")

class PhotoCaptioningPeriod(Period):
    """
    預期：server 分析圖片完畢

    下一個狀態：使用者決策（User Actioning）

    前一個狀態：閑置（None）
    
    """

    async def handle_interrupt_message(self, user: User, msg_type: str=None):
        """解讀圖片時，使用者傳送訊息打擾，可使用此方法處理回應"""
        if msg_type not in ("Text Message", "Image Message"):
            msg_type = "Text Message"

        # 建立Text Message，用文字訊息回應各種類型的打擾
        await super().handle_interrupt_message(user, msg_type)
        
    async def photo_captioning(self, user: User):
        """
        類型：server類觸發，不會頻繁觸發

        先回傳訊息“我在看看”，然後對圖片進行分析，最後再推送結果給用戶(已附上 qr menu)

        """
        # 更新狀態至 Photo Captioning(會耗時，給一個狀態)
        user.update_state(Action.PHOTO_RECEIVED)

        await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=self.event.reply_token,
                messages=[TextMessage(text="我來看看🧐")])
        )
    
        # 獲取圖片的二進制内容
        message_content = await async_messaging_api.get_message_content(self.event.message.id, async_req=True).get()

        # 對二進制内容進行下載圖片
        self.image_path = PathTool.join_path("app/downloads", f"image{user.id}.jpg")
        await asyncio.to_thread(ImageHelper.download_binary_stream, message_content, self.image_path)

        # 讀取圖片
        image_file = Image.open(self.image_path)
        
        # [呼叫模型] 進行分析，獲取圖片描述
        eng_caption = await asyncio.to_thread(image2text.img_to_text, image_file)

        # [呼叫模型] 翻譯成中文
        cn_caption =  await asyncio.to_thread(translator.translate_to_zh, eng_caption)
        
        # 推送caption給使用戶
        quick_reply_menu = UserActioningPeriod.creat_quick_reply_menu(user, cn_caption)
        response = await async_line_bot_api.push_message(
            PushMessageRequest(
                to=user.id,
                messages=[TextMessage(
                    text=f"“{cn_caption}”",
                    quick_reply=quick_reply_menu
                )]
            )
        )
        user.update_photo_caption(cn_caption)
        user.update_state(Action.GENERATED)

        linebot_logger.info(f"[class] PhotoCaptioningPeriod: {cn_caption=}")
        return cn_caption


class UserActioningPeriod:
    """
    預期：poetback（quick reply）

    下一個狀態：故事生成（Story Generating），調整故事（Modifying）

    前一個狀態：解讀圖片（Photo Captioning）->server完成、調整故事（Modifying）->覆蓋、延展
    """
    def __init__(self, event):
        self.event = event
    
    async def resend_menu_select_message(self, user: User):
        """
        傳送用戶選擇功能（quick reply）

        Args:
            user (User): 觸發event的用戶
            image_description (str, Optional): 圖片描述，若爲空會從user staging file裏面獲取
            interupt (bool): 是否爲打擾訊息，判斷有沒有reply_message可用
        
        """
        # 建立Quick Reply，重新要求選擇        
        quick_reply_menu = self.creat_quick_reply_menu(user)
        
        await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=self.event.reply_token,
                messages=[
                    TextMessage(text=f"“{user.image_caption}”"),
                    TextMessage(
                    text="你可以延申故事劇情或修改内容哦~👇", 
                    quick_reply=quick_reply_menu
                    )
                ]
            )
        )

    @staticmethod
    def creat_quick_reply_menu(user: User, image_description:str = None) -> QuickReply:
        menu = QuickReplyMenu()
        quick_reply_template = menu.get_template(Status.USER_ACTIONING)
        
        linebot_logger.info(f"{quick_reply_template=}")
        
        # 若不提供 description 則使用 user 裏 caching 的内容
        if image_description is None:
            image_description = user.image_caption
        
        # 為postback資料準備照片描述
        for item in quick_reply_template:
            item["data"]["message"] = image_description
        
        linebot_logger.info(f"[class] UserActioningPeriod: {quick_reply_template}")
        return quick_reply(quick_reply_template)

    
class CaptionModifyingPeriod:
    def __init__(self, event):
        self.event = event
    
    async def inform_modifying_start(self, user: User):
        response = await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[TextMessage(text="好，調整完傳送回來！")]
            )
        )
        
        user.update_state(Action.MODIFY_REQUEST)

    async def update_photo_caption_by_user(self, user: User):
        if user.current_status == Status.CAPTION_MODIFYING:
            user_produced_caption = self.event.message.text
            
            # 更新至 user cache
            user.update_photo_caption(user_produced_caption)
            
            quick_reply_menu = UserActioningPeriod.creat_quick_reply_menu(user, user_produced_caption)
            response = await async_line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=self.event.reply_token,
                    messages=[
                        TextMessage(text="已幫你修改為："),
                        TextMessage(text=user.image_caption,
                                    quick_reply=quick_reply_menu)
                    ]
                )
            )
            user.update_state(Action.MODIFYED)


class StoryGeneratingPeriod(Period):
    """
    預期：模型完成創作

    下一個狀態：故事預覽（Story Preview）

    前一個狀態：使用者決策（User Actioning）->選擇類型、故事預覽（Story Preview）->延申故事
    
    """

    async def handle_interrupt_message(self, user: User, msg_type: str = None):
        if msg_type not in ("Text Message", "Image Message"):
            msg_type = "Text Message"
        await super().handle_interrupt_message(user, msg_type)
    
    async def handle_generating_story(self, user: User, type: str=None, msg: str=None):
        """
        * UserActiongPeriod必須附帶type，需記錄
        """
        # 若爲 User Actioning，必須有type
        if user.current_status == Status.USER_ACTIONING:
            # 確保參數去傳遞
            if type is None:
                raise f"User Actioning 必須提供類型才能生成故事。"
            if msg is None:
                raise f"User Actioning 必須提供描述内容生成故事。"
            
            # 記錄進 user cache
            msg_for_qr = msg
            user.save_story_type(type)
            user.update_state(Action.TYPE_COMFIRM)
        elif user.current_status == Status.STORY_PREVIEW:
            # 從 user cache 取出内容使用
            msg_for_qr = None   # story 會超出字數限制，先禁用，采用cache撈的方式
            type = user.story_type
            msg = user.story_list
            user.update_state(Action.STORY_EXTEND)
        else:
            raise f"{user.current_status} is not allow to generating story."

        # 發送已收到訊息
        await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[TextMessage(text="讓我想想吼~~（努力思考中🤔")]
            )
        )

        # AI創作故事，預計30秒,staging 至 user
        story = await self.__generating_story(type, msg)
        user.append_story_list(story)

        # 建立功能選單
        quick_reply_menu = StoryPreviewPeriod.creat_quick_reply_menu(user, msg_for_qr)
        
        # 回應生成結果+選單給用戶
        await async_line_bot_api.push_message(
            PushMessageRequest(
                to=user.id,
                messages=[TextMessage(
                    text=story,
                    quick_reply=quick_reply_menu
                )]
            )
        )
        # 更新狀態：已完成故事
        user.update_state(Action.GENERATED)


    async def __generating_story(self, type: str, data: Union[str, list] = None):
        """
        Args:
            user (User): 此 event 用戶
            type (str): 故事延展類型
            msg (str): 故事生成依照的參考内容
        """
        system_prompt_1 = [
            {
                'role': 'system', 
                'content': (
                    "你是一位專業的故事創作者，擅長將簡單的圖片描述轉化為生動的故事。你的目標是根據使用者提供的圖片描述內容和指定的故事類型，創作一個短篇故事。\n\n"
                    "以下是你的要求：\n"
                    "1. 充分理解圖片描述內容，讓故事與描述緊密相關。\n"
                    f"2. 根據故事類型\"{type}\" 來創作，確保故事風格符合該類型的特點。\n"
                    "3. 生成的故事應包含完整的開頭、發展、高潮和結局，字數控制在 100 至 200 字之間，緊湊而精彩。\n\n"
                    "請專注於創造力，並確保故事具有吸引力和清晰的結構。\n"
                    "故事包括以下結構：\n"
                    "1. 開始：簡短描述背景和主要角色。\n"
                    "2. 中間：設置角色面臨的挑戰或衝突，並描寫解決方案。\n"
                    "3. 結尾：故事需要有一個合理的結局（開放式結尾需緊扣主題）。\n"
                    "注意：\n"
                    "- 故事應避免重複段落。\n"
                    "- 每段情節應有邏輯銜接，避免跳躍式情節發展。\n"
                )
            }
        ]

        system_prompt_2 = [
            {
                'role': 'system', 
                'content': (
                    "你是一位專業的故事創作者，擅長延續現有的故事劇情並創作出有趣的後續發展。你的目標是根據使用者提供的故事情節和指定的故事類型，接續創作一段新的故事內容。\n\n"
                    "以下是你的要求：\n"
                    "1. 仔細閱讀並理解現有的故事劇情，讓你的創作與之前的內容自然銜接。\n"
                    f"2. 根據故事類型-\"{type}\"，確保後續故事符合該類型的特點。\n"
                    "3. 創作的後續故事應包含合理的發展和清晰的邏輯，字數控制在 150 至 250 字之間。\n\n"
                    "請確保故事生動有趣，並為情節的發展增添吸引力。\n"
                    "故事包括以下結構：\n"
                    "1. 開始：簡短描述背景和主要角色。\n"
                    "2. 中間：設置角色面臨的挑戰或衝突，並描寫解決方案。\n"
                    "3. 結尾：故事需要有一個合理的結局（開放式結尾需緊扣主題）。\n"
                    "注意：\n"
                    "- 故事應避免重複段落。\n"
                    "- 每段情節應有邏輯銜接，避免跳躍式情節發展。\n"
                )
            }
        ]

        word_num = 500
        # 圖片描述
        if isinstance(data, str):
            user_input = data
            chat_history = system_prompt_1
        # 故事劇情
        else:
            user_input = ""
            chat_history = system_prompt_2
            for story in data:
                user_input += f"{story}\n"
                word_num += 120

        story = await asyncio.to_thread(
            mandrine_llm.generate_text, 
            user_input, 
            chat_history, 
            word_num
            )
        return story
    

class StoryPreviewPeriod:
    def __init__(self, event):
        self.event = event
    
    async def resend_menu_select_message(self, user: User):
        quick_reply_menu = self.creat_quick_reply_menu(user)

        await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[
                    TextMessage(text=user.story_list[-1]),
                    TextMessage(
                        text="你想調整還是結案呢？" if user.story_size >=LineBot.MAX_STORY_SIZE else "你想繼續延申，調整還是結案呢？",
                        quick_reply=quick_reply_menu
                    )
                ]
            )
        )

    @staticmethod
    def creat_quick_reply_menu(user: User, story:str = None) -> QuickReply:
        menu = QuickReplyMenu()
        quick_reply_template = menu.get_template(Status.STORY_PREVIEW)
        
        linebot_logger.info(f"{quick_reply_template=}")
        
        if user.story_size >= LineBot.MAX_STORY_SIZE:
            # TODO 需優化為對 extend 來刪
            del quick_reply_template[0] # 把AI延展功能刪除（index 0）
            del quick_reply_template[1] # 把使用者延展功能刪除（index 1）

        return quick_reply(quick_reply_template)

class StoryModifyingPeriod:
    def __init__(self, event):
        self.event = event
    
    async def inform_modifying_start(self, user: User):
        response = await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[TextMessage(text="好，調整完傳送回來！")]
            )
        )
        
        user.update_state(Action.MODIFY_REQUEST)
    
    async def inform_produce_start(self, user: User):
        response = await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[TextMessage(text="好，現在換你接手！")]
            )
        )
        
        user.update_state(Action.USER_PRODUCE_REQUEST)

    async def update_story_by_user(self, user: User):
        if user.current_status == Status.STORY_MODIFYING:
            user_modified_story = self.event.message.text
            
            # 更新至 user cache
            user.update_story_list(user_modified_story)
            
            quick_reply_menu = StoryPreviewPeriod.creat_quick_reply_menu(user, user_modified_story)
            response = await async_line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=self.event.reply_token,
                    messages=[
                        TextMessage(text="已幫你修改為："),
                        TextMessage(text=user.story_list[-1],
                                    quick_reply=quick_reply_menu)
                    ]
                )
            )
            user.update_state(Action.MODIFYED)

    async def append_story_by_user(self, user: User):
        if user.current_status == Status.STORY_USER_PRODUCING:
            user_produced_story = self.event.message.text
            
            # 更新至 user cache
            user.append_story_list(user_produced_story)
            
            quick_reply_menu = StoryPreviewPeriod.creat_quick_reply_menu(user, user_produced_story)
            response = await async_line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=self.event.reply_token,
                    messages=[
                        TextMessage(text="以下為後續的劇情發展："),
                        TextMessage(text=user.story_list[-1],
                                    quick_reply=quick_reply_menu)
                    ]
                )
            )
            user.update_state(Action.USER_PRODUCED)


class AudioGeneratingPeriod:
    """
    結束后，會生成音檔，但是是默認進行，不告訴
    
    下一個狀態：閑置（None）

    前一個狀態：故事預覽（Story Preview）->完成故事、使用者決策（User Actioning）->結束

    """
    def __init__(self, event):
        self.event = event

    # 沒有 handle_interrupt_message，背景生成錄音及回傳，也不回應訊息，儘快完成 audio 發送
    # 但處理接收照片回應，因爲用戶會默認為 閑置狀態而發照片
    async def send_waiting_sticker(self, user: User):
        await async_line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=self.event.reply_token,
                messages=[StickerMessage(
                    packageId="8525",
                    stickerId="16581311"
                )]
            )
        )
    async def generating_audio(self, user: User):
        user.update_state(Action.STORY_CLOSED)
        # 故事音檔
        if user.story_size:
            for story in user.story_list:
                audio_name, duration = await asyncio.to_thread(speech.generate_speech, story, user.id)
                response = await async_line_bot_api.push_message(
                    PushMessageRequest(
                        to=user.id,
                        messages=[AudioMessage(
                            originalContentUrl=f"{EnvConfig.ngrok_url}/line/static/audio/{audio_name}",
                            duration=duration
                        )]
                    )
                )
        else:
            # 圖片描述音檔
            audio_name, duration = await asyncio.to_thread(speech.generate_speech, user.image_caption, user.id)
            response = await async_line_bot_api.push_message(
                        PushMessageRequest(
                            to=user.id,
                            messages=[AudioMessage(
                                originalContentUrl=f"{EnvConfig.ngrok_url}/line/static/audio/{audio_name}",
                                duration=duration
                            )]
                        )
                    )
        user.update_state(Action.GENERATED)
        user.clear_user_file()
        