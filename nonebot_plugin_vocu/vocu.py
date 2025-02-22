import httpx
import asyncio
from dataclasses import dataclass, fields
from .config import config


# @dataclass
# class Prompt:
#     id: str
#     name: str
#     promptOriginAudioStorageUrl: str


# @dataclass
# class Metadata:
#     avatar: str
#     description: str
#     prompts: list[Prompt] = field(default_factory=list)


@dataclass
class Role:
    id: str
    idForGenerate: str | None
    name: str
    status: str
    # metadata: Metadata

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

    def handle_error(self, response):
        status = response.get("status")
        if status != 200:
            raise Exception(f"status: {status}, message: {response.get('message')}")

    # https://v1.vocu.ai/api/tts/voice
    # query参数: showMarket default=false
    async def list_roles(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://v1.vocu.ai/api/tts/voice",
                headers=self.auth,
                params={"showMarket": "true"},
            )
        response = response.json()
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
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://v1.vocu.ai/api/tts/voice/{id}", headers=self.auth
            )
        response = response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}"

    # https://v1.vocu.ai/api/voice/byShareId Body参数application/json {"shareId": "string"}
    async def add_role(self, share_id: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://v1.vocu.ai/api/voice/byShareId",
                headers=self.auth,
                json={"shareId": share_id},
            )
        response = response.json()
        self.handle_error(response)
        await self.list_roles()
        return f"{response.get('message')}, voiceId: {response.get('voiceId')}"

    async def sync_generate(
        self, voice_id: str, text: str, prompt_id: str | None = None
    ) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://v1.vocu.ai/api/tts/simple-generate",
                headers=self.auth,
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
            )
        response = response.json()
        self.handle_error(response)
        return response.get("data").get("audio")

    async def async_generate(
        self, voice_id: str, text: str, prompt_id: str | None = None
    ) -> str:
        # https://v1.vocu.ai/api/tts/generate
        # 提交 任务
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://v1.vocu.ai/api/tts/generate",
                headers=self.auth,
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
            )
        response = response.json()
        self.handle_error(response)
        # 获取任务 ID
        task_id: str = response.get("data").get("id")
        if not task_id:
            raise Exception("获取任务ID失败")
        # 轮训结果 https://v1.vocu.ai/api/tts/generate/{task_id}?stream=true
        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://v1.vocu.ai/api/tts/generate/{task_id}?stream=true",
                    headers=self.auth,
                )
            response = response.json()
            data = response.get("data")
            if data.get("status") == "generated":
                return data["metadata"]["contents"][0]["audio"]
            # 根据 text 长度决定 休眠时间
            await asyncio.sleep(3)

    async def fetch_histories(self, limit: int = 10) -> list[str]:
        # https://v1.vocu.ai/api/tts/generate?offset=20&limit=20&stream=true
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://v1.vocu.ai/api/tts/generate?offset=0&limit={limit}&stream=true",
                headers=self.auth,
            )
        response = response.json()
        self.handle_error(response)
        data_lst = response.get("data")
        if not data_lst and not isinstance(data_lst, list):
            raise Exception("获取历史记录失败")

        # 生成历史记录
        self.histories = [
            History(
                role_name=data["metadata"]["voices"][0]["name"],
                text=data["metadata"]["contents"][0]["text"],
                audio=data["metadata"]["contents"][0]["audio"],
            )
            for data in data_lst
        ]

        return [str(history) for history in self.histories]
