from nonebot import get_plugin_config

# from pathlib import Path
from pydantic import BaseModel
from typing import List, Literal, Optional  # noqa: F401

# from nonebot_plugin_apscheduler import scheduler  # noqa: F401
# import nonebot_plugin_localstore as store


class Config(BaseModel):
    vocu_api_key: str


# cache_dir: Path = store.get_plugin_cache_dir()
# config_dir: Path = store.get_plugin_config_dir()
# data_dir: Path = store.get_plugin_data_dir()

# 配置加载
config: Config = get_plugin_config(Config)
# gconfig = get_driver().config

# 全局名称
# NICKNAME: str | None = next(iter(gconfig.nickname), None)
