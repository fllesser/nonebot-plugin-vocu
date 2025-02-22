import re

from nonebot.plugin.on import on_regex, on_command
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Bot, MessageEvent
from nonebot.consts import REGEX_MATCHED
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from .vocu import VocuClient
from .config import config

vocu = VocuClient()


# xxx说xxx
@on_regex(r"(.+)说(.*)").handle()
async def _(matcher: Matcher, bot: Bot, event: MessageEvent):
    matched: re.Match[str] = matcher.state[REGEX_MATCHED]
    role_name = matched.group(1).strip()
    content = matched.group(2).strip()
    # 校验 role_name
    if len(role_name) > 10:
        await matcher.finish()
    try:
        voice_id = await vocu.get_role_by_name(role_name)
    except Exception:
        await matcher.finish()
    # 补充回复消息
    if reply := event.reply:
        content += reply.message.extract_plain_text().strip()

    # 校验文本长度
    if len(content) > config.vocu_chars_limit:
        await matcher.finish(f"不能超过 {config.vocu_chars_limit} 字符")
    # 提示用户
    await bot.call_api(
        "set_msg_emoji_like", message_id=event.message_id, emoji_id="282"
    )
    try:
        if config.vocu_request_type == "sync":
            audio_url = await vocu.sync_generate(voice_id, content)
        else:
            audio_url = await vocu.async_generate(voice_id, content)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send(MessageSegment.record(audio_url))


@on_command("vocu.list", aliases={"角色列表"}, priority=10, block=True).handle()
async def _(matcher: Matcher, bot: Bot):
    await vocu.list_roles()
    await matcher.send(
        MessageSegment.node_custom(
            user_id=int(bot.self_id), nickname="角色列表", content=vocu.fmt_roles
        )
    )


@on_command("vocu.del", priority=10, block=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    idx = args.extract_plain_text().strip()
    if not idx.isdigit():
        await matcher.finish("请输入正确的序号")
    idx = int(idx) - 1
    if idx < 0 or idx >= len(vocu.roles):
        await matcher.finish("请输入正确的序号")
    try:
        msg = await vocu.delete_role(idx)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send("删除角色成功 " + msg)


@on_command("vocu.add", priority=10, block=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    share_id = args.extract_plain_text().strip()
    try:
        msg = await vocu.add_role(share_id)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send("添加角色成功 " + msg)


@on_command("vocu.history", aliases={"历史生成"}, priority=10, block=True).handle()
async def _(matcher: Matcher, bot: Bot, args: Message = CommandArg()):
    limit = args.extract_plain_text().strip()
    limit = 10 if not limit.isdigit() else int(limit)
    try:
        histories: list[str] = await vocu.fetch_histories(limit)
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
    if idx < 0 or idx >= len(vocu.histories):
        await matcher.finish("请输入正确的序号")
    audio_url = vocu.histories[idx].audio
    await matcher.send(MessageSegment.record(audio_url))
