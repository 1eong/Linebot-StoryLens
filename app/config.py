"""
Here is the global config file.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv
from dataclasses import dataclass


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


class LineBot:
    channel_access_token: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    channel_secret: str = os.getenv("LINE_CHANNEL_SECRET")


class HuggingFace:
    access_token: str = os.getenv("HUGGINGFACE_ACCESS_TOKEN")


@dataclass
class Config:
    app_info = AppInfo()
    env_config = EnvConfig()
