from nonebot.plugin import PluginMetadata

from .config import Config
from .matcher import vocu  # noqa: E402, F401

__plugin_meta__ = PluginMetadata(
    name="Vocu 语音插件",
    description="vocu.ai 语音合成",
    usage="雷军说我开小米苏七，创死你们这群哈逼(支持回复消息)",
    type="application",  # library
    homepage="https://github.com/fllesser/nonebot-plugin-vocu",
    config=Config,
    # supported_adapters=inherit_supported_adapters(
    #     "nonebot_plugin_alconna", "nonebot_plugin_uninfo"
    # ),
    supported_adapters={"~onebot.v11"},
    extra={"author": "fllesser <fllessive@gmail.com>"},
)
