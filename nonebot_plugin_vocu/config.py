from nonebot import get_plugin_config

from pydantic import BaseModel
from typing import Literal


class Config(BaseModel):
    vocu_api_key: str = ""
    vocu_request_type: Literal["async", "sync"] = "async"
    vocu_chars_limit: int = 100


config: Config = get_plugin_config(Config)
