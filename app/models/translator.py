import torch
from enum import Enum
from transformers import T5ForConditionalGeneration, T5Tokenizer
from app.utils.logger import model_logger

def check(model_name: str, tag: str = None):
    if torch.cuda.is_available():
        # 顯存總量（MB）
        total_memory = torch.cuda.get_device_properties(0).total_memory / 1024**2
        # 已使用顯存（MB）
        allocated_memory = torch.cuda.memory_allocated(0) / 1024**2
        # 剩餘顯存（MB）
        free_memory = total_memory - allocated_memory

        model_logger.info(f"[{model_name}] {tag} - GPU Total Memory: {total_memory:.2f} MB")
        model_logger.info(f"[{model_name}] {tag} - GPU Allocated Memory: {allocated_memory:.2f} MB")
        model_logger.info(f"[{model_name}] {tag} - GPU Free Memory: {free_memory:.2f} MB")
    else:
        model_logger.info("No GPU detected!")

class Language(Enum):
    ZH = "translate to zh: "
    EN = "translate to en: "

class Translator:
    def __init__(self):
        self.model_name = 'utrobinmv/t5_translate_en_ru_zh_small_1024'
        self.model = None
        self.tokenizer = None

    def __load_model(self):
        if self.model is not None:
            del self.model
            torch.cuda.empty_cache()  # 清理缓存

        self.model = T5ForConditionalGeneration.from_pretrained(self.model_name).to('cuda')
        self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)

    def translate_to_zh(self, user_input: str):
        check(self.__class__.__name__, "translate")
        self.__load_model()
        # translate to Chinese
        reply = self.__translate(user_input, Language.ZH)

        self.__clear()
        return reply
    
    def __translate(self, user_input: str, translate_to: Language = Language.ZH) -> str:
        src_text = translate_to.value + user_input

        input_ids = self.tokenizer(src_text, return_tensors="pt")

        generated_tokens = self.model.generate(**input_ids.to('cuda'))

        result = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
        
        check(self.__class__.__name__, f"translate_result={result}")
        return result[0]
        
    def __clear(self):
        """清理模型和缓存"""
        if hasattr(self, 'model') and self.model is not None:
            del self.model
            self.model = None
        if hasattr(self, 'tokenizer') and self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        torch.cuda.empty_cache()
        check(self.__class__.__name__, "clear")


translator = Translator()
