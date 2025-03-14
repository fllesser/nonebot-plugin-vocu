from nonebot.plugin import PluginMetadata

from .config import Config

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

import re

from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, RegexMatched
from nonebot.permission import SUPERUSER
from nonebot.plugin.on import on_command, on_regex

from .config import config
from .vocu import VocuClient

vocu_client = VocuClient()


# xxx说xxx
@on_regex(r"(.+?)说(.*)").handle()
async def _(
    matcher: Matcher,
    bot: Bot,
    event: MessageEvent,
    matched: re.Match[str] = RegexMatched(),
):
    role_name = matched.group(1).strip()
    content = matched.group(2).strip()
    # 校验 role_name
    # if len(role_name) > 10:
    #     await matcher.finish()
    try:
        voice_id = await vocu_client.get_role_by_name(role_name)
    except Exception:
        await matcher.finish()
    # 补充回复消息
    if reply := event.reply:
        content += reply.message.extract_plain_text().strip()

    # 校验文本长度
    if len(content) > config.vocu_chars_limit:
        await matcher.finish(f"不能超过 {config.vocu_chars_limit} 字符")
    # 提示用户
    await bot.call_api("set_msg_emoji_like", message_id=event.message_id, emoji_id="282")
    try:
        if config.vocu_request_type == "sync":
            audio_url = await vocu_client.sync_generate(voice_id, content)
        else:
            audio_url = await vocu_client.async_generate(voice_id, content)
    except Exception as e:
        await matcher.finish(str(e))
    # 下载语音到缓存
    audio_path = await vocu_client.download_audio(audio_url)
    await matcher.send(MessageSegment.record(audio_path))


@on_command("vocu.list", aliases={"角色列表"}, priority=10, block=True).handle()
async def _(matcher: Matcher, bot: Bot):
    await vocu_client.list_roles()

    roles = [f"{i + 1}. {role}" for i, role in enumerate(vocu_client.roles)]
    roles = ["\n".join(roles[i : i + 10]) for i in range(0, len(roles), 10)]

    nodes = [MessageSegment.node_custom(user_id=int(bot.self_id), nickname="角色列表", content=role) for role in roles]
    await matcher.send(Message(nodes))


@on_command("vocu.del", priority=10, block=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    idx = args.extract_plain_text().strip()
    if not idx.isdigit():
        await matcher.finish("请输入正确的序号")
    idx = int(idx) - 1
    if idx < 0 or idx >= len(vocu_client.roles):
        await matcher.finish("请输入正确的序号")
    try:
        msg = await vocu_client.delete_role(idx)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send("删除角色成功 " + msg)


@on_command("vocu.add", priority=10, block=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    share_id = args.extract_plain_text().strip()
    try:
        msg = await vocu_client.add_role(share_id)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send("添加角色成功 " + msg)


@on_command("vocu.history", aliases={"历史生成"}, priority=10, block=True).handle()
async def _(matcher: Matcher, bot: Bot, args: Message = CommandArg()):
    size = args.extract_plain_text().strip()
    size = 20 if not size.isdigit() else int(size)
    try:
        histories: list[str] = await vocu_client.fetch_mutil_page_histories(size)
    except Exception as e:
        await matcher.finish(str(e))
    nodes = [
        MessageSegment.node_custom(
            user_id=int(bot.self_id),
            nickname="历史生成记录",
            content=f"{i + 1}-{history}",
        )
        for i, history in enumerate(histories)
    ]
    await matcher.send(Message(nodes))


@on_command("vocu", priority=10, block=True).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    idx = args.extract_plain_text().strip()
    if not idx.isdigit():
        await matcher.finish("请输入正确的序号")
    idx = int(idx) - 1
    if idx < 0 or idx >= len(vocu_client.histories):
        await matcher.finish("请输入正确的序号")
    audio_url = vocu_client.histories[idx].audio
    audio_path = await vocu_client.download_audio(audio_url)
    await matcher.send(MessageSegment.record(audio_path))
