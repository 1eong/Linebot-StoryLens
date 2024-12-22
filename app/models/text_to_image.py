from app.config import HuggingFace
import torch
from huggingface_hub import hf_hub_download
from diffusers import DiffusionPipeline
from cog_sdxl.dataset_and_utils import TokenEmbeddingsHandler
from app.utils.utils import PathTool
from diffusers import AutoPipelineForText2Image
from app.utils.image_utils import  ImageHelper

from app.models.translator import check
import gc

access_token = HuggingFace.access_token
# api = HfApi()
# api.list_models(token=access_token)

class Emoji:
    def __init__(self):
        self.model_name = "fofr/sdxl-emoji"
    
    def __load_model(self):

        self.pipe = DiffusionPipeline.from_pretrained(
                "stabilityai/stable-diffusion-xl-base-1.0",
                torch_dtype=torch.float16,
                variant="fp16",
        ).to("cuda")
        self.pipe.load_lora_weights(self.model_name, weight_name="lora.safetensors")

    def generate_image(self, prompt:str="A <s0><s1> emoji of a man"):
        check("before load")
        self.__load_model()
        text_encoders = [self.pipe.text_encoder, self.pipe.text_encoder_2]
        tokenizers = [self.pipe.tokenizer, self.pipe.tokenizer_2]

        embedding_path = hf_hub_download(repo_id=self.model_name, filename="embeddings.pti", repo_type="model")
        embhandler = TokenEmbeddingsHandler(text_encoders, tokenizers)
        embhandler.load_embeddings(embedding_path)
        images = self.pipe(
            prompt,
            num_inference_steps=10,
            height=64,
            width=64,
            cross_attention_kwargs={"scale": 0.8},
        ).images
        check("after load")
        self.__clear()
        check("after clear")
        #your output image
        images[0]
        print(type(images[0]))
        images[0].save(PathTool.join_path("app","downloads","emoji.jpg"), format="JPEG")
        # ImageHelper.download_binary_stream(images[0], PathTool.join_path("app","downloads","emoji.jpg"))
        
        return images[0]
    
    def __clear(self):
        if hasattr(self, 'pipe'):
            del self.pipe  # 刪除 pipeline 對象
            self.pipe = None
        torch.cuda.empty_cache()
        gc.collect()

class HandWritingImage:

    def __init__(self):
        self.model_name = "fofr/flux-handwriting"

    def __load_image(self):
        self.pipeline = AutoPipelineForText2Image.from_pretrained(
            'black-forest-labs/FLUX.1-dev', 
            torch_dtype=torch.float16
            ).to('cuda')
        self.pipeline.load_lora_weights(self.model_name, weight_name='lora.safetensors')
        
    def generate_image(self, input_text: str):
        check("handwriting before load")
        self.__load_image()
        check("handwriting after load")
        image = self.pipeline(input_text).images[0]
        self.__clear()
        check("handwriting after clear")
        return image
    
    def __clear(self):
        if hasattr(self, 'pipeline'):
            del self.pipeline  # 刪除 pipeline 對象
            self.pipeline = None
        torch.cuda.empty_cache()