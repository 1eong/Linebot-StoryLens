"""
Here is the global config file.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from dataclasses import dataclass
import torch


@lru_cache
def get_config():
    env_filepath = f".env.{os.getenv('APP_MODE', 'dev')}"
    load_dotenv(env_filepath)
    return Config()


class AppInfo:
    app_name: str = "StoryLens"
    author: str = "Daniel Leong"


class EnvConfig:
    app_mode: str = os.getenv("APP_MODE")
    host: str = "127.0.0.1"
    port: int = int(os.getenv("PORT"))
    reload: bool = bool(os.getenv("RELOAD"))
    ngrok_url: str = os.getenv("NGROK")


class LineBot:
    channel_access_token: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    channel_secret: str = os.getenv("LINE_CHANNEL_SECRET")
    MAX_STORY_SIZE: int = 4     

class HuggingFace:
    access_token: str = os.getenv("HUGGINGFACE_ACCESS_TOKEN")
    model_device: str = torch.cuda.get_device_name() if torch.cuda.is_available() else "cpu"
    pytorch_version: str = torch.__version__


@dataclass
class Config:
    app_info = AppInfo()
    env_config = EnvConfig()
