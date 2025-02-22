import httpx

from dataclasses import dataclass, field
from .config import config


@dataclass
class Prompt:
    id: str
    name: str
    promptOriginAudioStorageUrl: str


@dataclass
class Metadata:
    avatar: str
    description: str
    prompts: list[Prompt] = field(default_factory=list)


@dataclass
class Role:
    id: str
    idForGenerate: str | None
    name: str
    status: str
    metadata: Metadata

    # _str_
    def __str__(self):
        return f"{self.name}({self.id})"


class VocuClient:
    def __init__(self):
        self.auth = {"Authorization": "Bearer " + config.vocu_api_key}
        self.roles: list[Role] = []

    @property
    def fmt_roles(self) -> str:
        # 序号 角色名称(角色ID)
        return "\n".join(
            f"{i + 1}. {role.name}({role.id})" for i, role in enumerate(self.roles)
        )

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
        self.roles = [Role(**role) for role in response.get("data")]
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
        id = role.idForGenerate if role.idForGenerate else role.id
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

    async def generate(
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
