import asyncio
from dataclasses import dataclass, fields
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import aiohttp
from nonebot import require
from nonebot.log import logger
from tqdm.asyncio import tqdm

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

from .config import config


@dataclass
class Role:
    """
    角色
    """

    id: str
    idForGenerate: str | None
    name: str
    status: str

    def __str__(self) -> str:
        return self.name


class VocuError(Exception):
    """
    vocu 错误
    """

    def __init__(self, message: str):
        self.message = message


def filter_role_data(data: dict) -> dict:
    allowed_fields = {f.name for f in fields(Role)}
    return {k: v for k, v in data.items() if k in allowed_fields}


@dataclass
class History:
    """
    历史记录
    """

    role_name: str
    text: str
    audio: str

    def __str__(self) -> str:
        return f"{self.role_name}: {self.text}\n{self.audio}"


class VocuClient:
    """
    vocu client
    """

    def __init__(self):
        self.roles: list[Role] = []
        self.histories: list[History] = []
        self._session: aiohttp.ClientSession | None = None

    @property
    async def session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            headers = {"Authorization": "Bearer " + config.vocu_api_key}
            self._session = aiohttp.ClientSession(
                headers=headers, proxy=config.vocu_proxy if config.vocu_proxy else None
            )
        return self._session

    @property
    def fmt_roles(self) -> str:
        # 序号 角色名称(角色ID)
        return "\n".join(f"{i + 1}. {role}" for i, role in enumerate(self.roles))

    def handle_error(self, response: dict):
        status = response.get("status")
        if status != 200:
            raise VocuError(f"status: {status}, message: {response.get('message')}")

    # https://v1.vocu.ai/api/tts/voice
    # query参数: showMarket default=false
    async def list_roles(self):
        """
        获取角色列表
        """
        session = await self.session
        async with session.get(
            "https://v1.vocu.ai/api/tts/voice",
            params={"showMarket": "true"},
        ) as response:
            response = await response.json()
        self.handle_error(response)
        self.roles = [Role(**filter_role_data(role)) for role in response.get("data")]
        return self.roles

    async def get_role_by_name(self, role_name: str) -> str:
        """
        根据角色名称获取角色ID
        """
        if not self.roles:
            await self.list_roles()
        for role in self.roles:
            if role.name == role_name:
                return role.idForGenerate if role.idForGenerate else role.id
        raise ValueError(f"找不到角色: {role_name}")

    # https://v1.vocu.ai/api/tts/voice/{id}
    async def delete_role(self, idx: int) -> str:
        """
        删除角色
        """
        role = self.roles[idx]
        id = role.id
        session = await self.session
        async with session.delete(f"https://v1.vocu.ai/api/tts/voice/{id}") as response:
            response = await response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}"

    # https://v1.vocu.ai/api/voice/byShareId Body参数application/json {"shareId": "string"}
    async def add_role(self, share_id: str) -> str:
        """
        添加角色
        """
        session = await self.session
        async with session.post(
            "https://v1.vocu.ai/api/voice/byShareId",
            json={"shareId": share_id},
        ) as response:
            response = await response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}, voiceId: {response.get('voiceId')}"

    async def generate(self, *, voice_id: str, text: str, prompt_id: str | None = None) -> str:
        """
        生成音频
        """
        if config.vocu_request_type == "sync":
            return await self.sync_generate(voice_id, text, prompt_id)
        return await self.async_generate(voice_id, text, prompt_id)

    async def sync_generate(self, voice_id: str, text: str, prompt_id: str | None = None) -> str:
        """
        同步生成音频
        """
        session = await self.session
        async with session.post(
            "https://v1.vocu.ai/api/tts/simple-generate",
            json={
                "voiceId": voice_id,
                "text": text,
                "promptId": prompt_id if prompt_id else "default",  # 角色风格
                "preset": "v2_creative",
                "flash": False,  # 低延迟
                "stream": False,  # 流式
                "srt": False,
                "seed": -1,
                # "dictionary": [], # 读音字典，格式为：[ ["音素", [["y", "in1"],["s" "u4"]]]]
            },
        ) as response:
            response = await response.json()
        self.handle_error(response)
        return response.get("data").get("audio")

    async def async_generate(self, voice_id: str, text: str, prompt_id: str | None = None) -> str:
        """
        异步生成音频
        """
        # https://v1.vocu.ai/api/tts/generate
        # 提交 任务
        session = await self.session
        async with session.post(
            "https://v1.vocu.ai/api/tts/generate",
            json={
                "contents": [
                    {
                        "voiceId": voice_id,
                        "text": text,
                        "promptId": prompt_id if prompt_id else "default",
                    },
                ],
                "break_clone": True,
                "sharpen": False,
                "temperature": 1,
                "top_k": 1024,
                "top_p": 1,
                "srt": False,
                "seed": -1,
            },
        ) as response:
            response = await response.json()
        self.handle_error(response)
        # 获取任务 ID
        task_id: str = response.get("data").get("id")
        if not task_id:
            raise Exception("获取任务ID失败")
        # 轮训结果 https://v1.vocu.ai/api/tts/generate/{task_id}?stream=true
        while True:
            session = await self.session
            async with session.get(
                f"https://v1.vocu.ai/api/tts/generate/{task_id}?stream=true",
            ) as response:
                response = await response.json()
            data = response.get("data")
            if data.get("status") == "generated":
                return data["metadata"]["contents"][0]["audio"]
            # 根据 text 长度决定 休眠时间
            await asyncio.sleep(3)

    async def fetch_mutil_page_histories(self, size: int = 20) -> list[str]:
        """
        获取多页历史记录
        """
        pages = size // 20
        pages = pages if pages < 5 else 5
        histories: list[History] = []
        for i in range(pages):
            try:
                histories.extend(await self.fetch_histories(i * 20, 20))
            except VocuError as e:
                logger.error(f"获取 {i * 20} - {i * 20 + 20} 的历史记录失败: {e}")
                break
        if not histories:
            raise VocuError("历史记录为空")
        self.histories = histories
        return [str(history) for history in histories]

    async def fetch_histories(self, offset: int = 0, limit: int = 20) -> list[History]:
        """
        获取历史记录
        """
        # https://v1.vocu.ai/api/tts/generate?offset=20&limit=20&stream=true
        session = await self.session
        async with session.get(
            f"https://v1.vocu.ai/api/tts/generate?offset={offset}&limit={limit}&stream=true"
        ) as response:
            response = await response.json()
        self.handle_error(response)
        data_lst = response.get("data")
        if not data_lst and not isinstance(data_lst, list):
            raise VocuError("history list is empty")

        # 生成历史记录
        histories: list[History] = []
        for data in data_lst:
            try:
                # 校验必要字段存在
                role_name = data["metadata"]["voices"][0]["name"]
                content = data["metadata"]["contents"][0]
                histories.append(
                    History(
                        role_name=role_name,
                        text=content["text"],
                        audio=content["audio"],
                    )
                )
            except (KeyError, IndexError):
                continue
        return histories

    async def download_audio(self, url: str) -> Path:
        """
        下载音频
        """
        # 生成文件名
        url_path = Path(urlparse(url).path)
        suffix = url_path.suffix if url_path.suffix else ".mp3"
        # 获取 url 的 md5 值
        url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
        file_name = f"{url_hash}{suffix}"
        file_path = store.get_plugin_cache_file(file_name)
        if file_path.exists():
            return file_path

        session = await self.session
        async with session.get(url) as response, aiofiles.open(file_path, "wb") as file:
            try:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0))
                with get_tqdm_bar(total=total, desc=file_name) as bar:
                    async for chunk in response.content.iter_chunked(1024 * 1024):
                        await file.write(chunk)
                        bar.update(len(chunk))
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if file_path.exists():
                    file_path.unlink()
                logger.error(f"url: {url}, file_path: {file_path} 下载过程中出现异常{e}")
                raise

        return file_path

    async def can_check_in(self) -> bool:
        """是否可以签到"""
        session = await self.session
        async with session.get("https://v1.vocu.ai/api/billing/checkin") as response:
            response = await response.json()

        return response.get("data").get("canCheckIn")

    async def captcha_verify(self, captcha_id: str, captcha_code: str) -> dict:
        """人机验证"""
        session = await self.session
        # 构建验证请求数据
        verify_data = {
            "collect": captcha_id,
            "tlg": "1752",
            "eks": "MZVzba1RhWAJ71UDIgbfhSssuLp/INPvuEjs2G0pZKlzJ41VXbfovy1KIhBDGeXNWW87ONidRcuzVfr4SqA8dcJtYRRKX+l538z+vro7JlUu5uHPRMQX3UGIPA354fqBZ6ficy+1vBjisW1wzuLBWMFH0GWH0LMNwPCzhRNc9LMHFBiWefZQfxPXX9dWD1P+Vi4QlBsoPqzEOC8/URBW62HNCo/LbJFoy/x9QUj/Uuc=",
            "sess": "s0EypqI97wMD2YFc_mBxxzlw9nRbLSVtgrpQvM5PcZjgVXzbPUer_HxRt1WVRVbrukb2hufz1fqPLDz8AaVF8njbPLhH4UxEXEpXjgcB5mqb_svMsD6E_A6SUgCUbr16Myr88E57JfTS_xuCJ4KOBPKBfWTgyJ-oYfbr5nBdSF_1nZwP5owFp3jBiIo96trADeEAn7C--J24F-Mylq5DBdVg0t4WyyYxEk_dByiyO-LmbpBWE-BbNEVBD90B32C0HguVMvndwSlxjhDVv9C9l46Y4Tf0uGcgqaQx8krDFsub1BM-b00OMj4l645zPjwp4JsXp7d3FlQnVC9O_59MGA_dLsaZfreqMXO6qAbeZ5C3CagHyfXX5Px2Pa685GXb12-khq3ypjmff5ggVGo1IEkPUAifj0MLzL4qKn55poEDVwDf01HjYjl6-7W3QRzaoG7DLfEZbxLYftL-81KevehXcz2KEhPX3W9opzPfx7gzQ*",
            "ans": captcha_code,
            "pow_answer": "2bd52605be127e58#211854",
            "pow_calc_time": "656",
        }

        # 设置验证请求的headers
        verify_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh,zh-CN;q=0.9,en;q=0.8,en-US;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://turing.captcha.gtimg.com",
            "Referer": "https://turing.captcha.gtimg.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",
        }

        async with session.post(
            "https://turing.captcha.qcloud.com/cap_union_new_verify", data=verify_data, headers=verify_headers
        ) as response:
            result = await response.json()

        return result

    async def daily_check_in(self):
        """
        每日签到
        """
        if not await self.can_check_in():
            return "今日已签到"

        session = await self.session

        # 第一步：进行人机验证
        # 这里需要获取验证码ID和答案，实际使用时可能需要用户交互
        # 暂时使用示例数据
        captcha_id = "+HHTPZVfaWRKMKy5oGAFMge3Ojsk1RKuQimZf6gPx4/sKmjfngzkWILbgBhvEmiLbkBchS2btGlC9Uhdax7Mt1sj7+YRkWNR5DfWFooB1ioGy5w0MKBbQVOvj9nG2lu1xEOSn8mzzcyg3yNfZ4zBc6tx+xjnL9k5AMVIC66+PJzTmhQz+R43MX6MCe7SmK8zKPd+8r4+UzshxThgxkL3LFhXiWCxVcJ0wqUpWOG5oMxUo8Zm0ZDHEB+Q/EWHcfP2dEGWPRwV2876T6NmlLVtTq39Gzw16KqD4uE4hxk4KCfn0pCpypffhUT7noISNLRFfctIfNM8RH3C2polU+1pzK5r6AKUKRJDGKHeii5YQ9Kph7EzFvN1YkxVVwQlhifsejgJH1ldTxpUo2OrZqFkvOyCpd/ibNpGmGvjlnqvBJfmCHvJu2NjUKz4wFCnrVqRcCLGq4xIzlI0esbsMlpZpw1ZfV8RwWlswTVJX4lTulmpt8Sh5usQnxHoQyk8tVQ2Y4lu6CbykjDwHZ8A6zb3Sac0RA+9DNOt8aYSJC4O2Glxlekq4s4c3LLPZzEXVhMaCNPiNTBysgn6I/4hdLLJRLOrg1WWEqYUBl6I7Il+1XHevL/9MU6FrVnnxe4Ums2IK/8coiG0CxJXcp929JlUv23aTE2b3Wu+S5hh4XHsIrVvO3vU/Un8njDyt6qgQz+0FsAKVoell0trz70gPmucq/zotP91AxXLDvRJvWzhPyKqx50WKN6mFDFjbPxR2V3ye9brCX4bWNJL/P8MMu8AhC76xNQKOAylrgda8QcChpdEM1VGLAXKmsw4B868qB8BliWh5lqXYF7QVwcju0UugbDC2+TuHZD4vYTQVKodLZTs6MhxWgG+eXN0laVgxTL3WUFj/oZyLCDfD6P9NRZWQ7GjmFza/XXJeNIvwEd9ma8aC7byiplKcmTMj/2uur6SlxIN4RPzrEFeVxy6M8cAz4avK9xB0Coehq8r3EHQKh7JybAxM38VgC/dP2byKZ+QnWGj4vfAg0i9VqQnKi2NID2WWbh68oQ5k3FxRrWEqlfefXMBAOOJmWl7csIE9ZR8gPNZPnoMMdyKj+iqxSGnjZekJ6rnUhzGyJoVUrddX0a4Hb+pXC7aybGszH+2j0X8Z9xeKpZEvunnxc+ucfffs2OWI9OBRSBPB8NhCMdeGSSfc4TqPXzjI8mcQV8kH8UpN6l95kAIdKjRgbxzvpPVu8exvkYS4NDnYUpzlS+jNVnwllVIk/jVyV21J8UpFSHEnj1NiV/UIa/CTTsRdUDE+f3R6zC++qv3v/wcLyD7wN5ltzkxOTorX0SBybm7j5pox+AIaxMceUqWOfDvbVm+DOejKWq1cFk2mtWqDSiGc4B41/8hXubWAp9tICJUJ12lKM4pzhugMzGOS+NLCqrBd8veZUQkhO4K4JlcnwrrHaGr5W+5V2ElE8U6Vszuxfxr+8Bq5R727iy298dSn18MqDDyt6qgQz+0GlzFM9jvpnRIdHkZ/0XLqVcUNPuW8htTEAb5h0HhmTSNWIvMtVIxZ/xbAHLZ/983TUiIFjpbR40trLL9DWmYymFrIOH+R4oYMgfBzXKnBoKvlXEC7Os4Ra5GmgofB0V3RGo49pVeuIA9tB/FZ0qLYTsNz0u0sYeIKICdHySzaBcw8reqoEM/tDDyt6qgQz+0gDWpGbGJZ3qLI3Tndnl3Q3btZKH9FR8xDn6kWHHSlniK81K15wrP4w=="
        captcha_code = '[{"elem_id":1,"type":"DynAnswerType_POS","data":"233,345"},{"elem_id":2,"type":"DynAnswerType_POS","data":"434,241"},{"elem_id":3,"type":"DynAnswerType_POS","data":"108,237"}]'

        try:
            verify_result = await self.captcha_verify(captcha_id, captcha_code)
            if verify_result.get("errorCode") != "0":
                return f"人机验证失败: {verify_result.get('errMessage')}"

            ticket = verify_result.get("ticket")
            randstr = verify_result.get("randstr")

            # 第二步：使用验证结果进行签到
            checkin_data = {
                "cp": None,
                "tcr": {
                    "appid": "194020629",
                    "ret": 0,
                    "ticket": ticket,
                    "randstr": randstr,
                    "verifyDuration": 92,
                    "actionDuration": 5091,
                    "sid": "7347105446483734528",
                },
            }

            async with session.post("https://v1.vocu.ai/api/billing/checkin", json=checkin_data) as response:
                result = await response.json()

            self.handle_error(result)
            return result.get("message")

        except Exception as e:
            logger.error(f"签到失败: {e}")
            return f"签到失败: {str(e)}"


def get_tqdm_bar(total: int, desc: str):
    return tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        dynamic_ncols=True,
        colour="green",
        desc=desc,
    )
