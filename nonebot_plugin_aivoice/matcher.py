import re

from nonebot.plugin.on import on_regex, on_command

from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.consts import REGEX_MATCHED
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from .vocu import VocuClient

vocu = VocuClient()


# xxx说xxx
@on_regex(r"(.+)说(.+)").handle()
async def _(matcher: Matcher):
    matched: re.Match[str] = matcher.state[REGEX_MATCHED]
    role_name, content = str(matched.groups(1)), str(matched.groups(2))

    try:
        voice_id = await vocu.get_role_by_name(role_name)
        # message_id: int = (await matcher.send("正在合成语音..."))["message_id"]
        audio_url = await vocu.generate(voice_id, content)
    except Exception as e:
        await matcher.finish(str(e))
    await matcher.send(MessageSegment.record(audio_url))
    # await bot.delete_msg(message_id=int(message_id))


@on_command("vocu.list", aliases={"角色列表"}, priority=10, block=True).handle()
async def _(matcher: Matcher):
    await vocu.list_roles()
    await matcher.send(vocu.fmt_roles)


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
        msg = str(e)
    await matcher.send("删除角色成功 " + msg)


@on_command("vocu.add", priority=10, block=True, permission=SUPERUSER).handle()
async def _(matcher: Matcher, args: Message = CommandArg()):
    share_id = args.extract_plain_text().strip()
    try:
        msg = await vocu.add_role(share_id)
    except Exception as e:
        msg = str(e)
    await matcher.send("添加角色成功 " + msg)
