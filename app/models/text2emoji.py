from huggingface_hub import HfApi
from app.config import HuggingFace
import torch
from huggingface_hub import hf_hub_download
from diffusers import DiffusionPipeline
from cog_sdxl.dataset_and_utils import TokenEmbeddingsHandler
from diffusers.models import AutoencoderKL
from functools import lru_cache

access_token = HuggingFace.access_token
# api = HfApi()
# api.list_models(token=access_token)


@lru_cache(maxsize=1)
def setup_model():
    pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
    ).to()

    # 加載 LoRA 權重
    pipe.load_lora_weights("fofr/sdxl-emoji", weight_name="lora.safetensors")

    # 啟用記憶體優化模式（例如 Attention Slicing）
    pipe.enable_attention_slicing()

    # 設置文本編碼器和 tokenizer
    text_encoders = [pipe.text_encoder, pipe.text_encoder_2]
    tokenizers = [pipe.tokenizer, pipe.tokenizer_2]

    # 加載嵌入文件
    embedding_path = hf_hub_download(
        repo_id="fofr/sdxl-emoji", filename="embeddings.pti", repo_type="model"
    )
    embhandler = TokenEmbeddingsHandler(text_encoders, tokenizers)
    embhandler.load_embeddings(embedding_path)
    return pipe


def text_to_emoji(prompt):
    # prompt="A <s0><s1> emoji of a man"
    pipe = setup_model()
    images = pipe(
        prompt,
        cross_attention_kwargs={"scale": 0.8},
    ).images
    # your output image
    images[0]
    print(f"{images[0]=}")
    return images[0]
