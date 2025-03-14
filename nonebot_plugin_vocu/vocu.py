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
    id: str
    idForGenerate: str | None
    name: str
    status: str

    def __str__(self):
        return self.name


def filter_role_data(data: dict) -> dict:
    allowed_fields = {f.name for f in fields(Role)}
    return {k: v for k, v in data.items() if k in allowed_fields}


@dataclass
class History:
    role_name: str
    text: str
    audio: str

    def __str__(self):
        return f"{self.role_name}: {self.text}\n{self.audio}"


class VocuClient:
    def __init__(self):
        self.auth = {"Authorization": "Bearer " + config.vocu_api_key}
        self.roles: list[Role] = []
        self.histories: list[History] = []

    @property
    def fmt_roles(self) -> str:
        # 序号 角色名称(角色ID)
        return "\n".join(f"{i + 1}. {role}" for i, role in enumerate(self.roles))

    def handle_error(self, response: dict):
        status = response.get("status")
        if status != 200:
            raise Exception(f"status: {status}, message: {response.get('message')}")

    # https://v1.vocu.ai/api/tts/voice
    # query参数: showMarket default=false
    async def list_roles(self):
        async with aiohttp.ClientSession(headers=self.auth) as session:
            async with session.get(
                "https://v1.vocu.ai/api/tts/voice",
                params={"showMarket": "true"},
            ) as response:
                response = await response.json()
        self.handle_error(response)
        self.roles = [Role(**filter_role_data(role)) for role in response.get("data")]
        return self.roles

    async def get_role_by_name(self, role_name: str) -> str:
        if not self.roles:
            await self.list_roles()
        for role in self.roles:
            if role.name == role_name:
                return role.idForGenerate if role.idForGenerate else role.id
        raise Exception(f"找不到角色: {role_name}")

    # https://v1.vocu.ai/api/tts/voice/{id}
    async def delete_role(self, idx: int) -> str:
        role = self.roles[idx]
        id = role.id
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"https://v1.vocu.ai/api/tts/voice/{id}", headers=self.auth) as response:
                response = await response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}"

    # https://v1.vocu.ai/api/voice/byShareId Body参数application/json {"shareId": "string"}
    async def add_role(self, share_id: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://v1.vocu.ai/api/voice/byShareId",
                headers=self.auth,
                json={"shareId": share_id},
            ) as response:
                response = await response.json()
        response = response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}, voiceId: {response.get('voiceId')}"

    async def sync_generate(self, voice_id: str, text: str, prompt_id: str | None = None) -> str:
        async with aiohttp.ClientSession(headers=self.auth) as session:
            async with session.post(
                "https://v1.vocu.ai/api/tts/simple-generate",
                data={
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
        # https://v1.vocu.ai/api/tts/generate
        # 提交 任务
        async with aiohttp.ClientSession(headers=self.auth) as session:
            async with session.post(
                "https://v1.vocu.ai/api/tts/generate",
                data={
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
            async with aiohttp.ClientSession(headers=self.auth) as session:
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
        pages = size // 20
        pages = pages if pages < 5 else 5
        histories: list[History] = []
        for i in range(pages):
            try:
                histories.extend(await self.fetch_histories(i * 20, 20))
            except Exception:
                break
        if not histories:
            raise Exception("获取历史记录失败")
        self.histories = histories
        return [str(history) for history in histories]

    async def fetch_histories(self, offset: int = 0, limit: int = 20) -> list[History]:
        # https://v1.vocu.ai/api/tts/generate?offset=20&limit=20&stream=true
        async with aiohttp.ClientSession(headers=self.auth) as session:
            async with session.get(
                f"https://v1.vocu.ai/api/tts/generate?offset={offset}&limit={limit}&stream=true"
            ) as response:
                response = await response.json()
        self.handle_error(response)
        data_lst = response.get("data")
        if not data_lst and not isinstance(data_lst, list):
            raise Exception("获取历史记录失败")

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
        file_name = generate_file_name(url)
        file_path = store.get_plugin_cache_file(file_name)
        if file_path.exists():
            return file_path

        async with aiohttp.ClientSession(
            headers=self.auth, timeout=aiohttp.ClientTimeout(total=300, connect=10.0)
        ) as session:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    with tqdm(
                        total=int(response.headers.get("Content-Length", 0)),
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                        dynamic_ncols=True,
                        colour="green",
                    ) as bar:
                        # 设置前缀信息
                        bar.set_description(file_name)
                        async with aiofiles.open(file_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(1024 * 1024):
                                await f.write(chunk)
                                bar.update(len(chunk))
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"url: {url}, file_path: {file_path} 下载过程中出现异常{e}")
                raise

        return file_path


def generate_file_name(url: str, suffix: str | None = None) -> str:
    # 根据 url 获取文件后缀
    path = Path(urlparse(url).path)
    suffix = path.suffix if path.suffix else suffix
    # 获取 url 的 md5 值
    url_hash = hashlib.md5(url.encode()).hexdigest()[:16]
    file_name = f"{url_hash}{suffix}"
    return file_name
