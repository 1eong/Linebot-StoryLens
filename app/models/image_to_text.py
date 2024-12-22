import torch
from PIL import ImageFile
from transformers import pipeline
from app.models.translator import check
from app.utils.logger import model_logger

class Img2Text:
    def __init__(self):
        self.model_name = "Salesforce/blip-image-captioning-large"

    def __load_model(self):
        check(self.__class__.__name__, "ready to loaded")
        self.pipeline = pipeline(
            task="image-to-text", 
            model=self.model_name
        )
        check(self.__class__.__name__, "model loaded")


    def img_to_text(self, image:ImageFile, max_new_tokens=70):
        """
        將圖像轉換為文字描述。
        :param image: 傳入的圖像（可以是文件路徑或 PIL.Image）。
        :param max_new_tokens: 生成文字的最大 token 長度。
        :return: 生成的文字描述。
        """
        self.__load_model() 
        result = self.pipeline(image, max_new_tokens=max_new_tokens)
        text = result[0].get("generated_text")
        self.__clear()
        return text
    
    def __clear(self):
        # 刪除 pipeline 和模型
        if hasattr(self, 'pipeline') and self.pipeline is not None:
            del self.pipeline.model  # 刪除模型
            del self.pipeline.tokenizer  # 刪除 tokenizer
            del self.pipeline  # 刪除 pipeline 對象
            self.pipeline = None
        torch.cuda.empty_cache()
        check(self.__class__.__name__, "clear")


image2text = Img2Text()
