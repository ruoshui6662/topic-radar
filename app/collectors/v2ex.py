"""V2EX 热帖：https://www.v2ex.com/api/topics/hot.json（实测可用）"""
from .base import BaseCollector, Item

_URL = "https://www.v2ex.com/api/topics/hot.json"


class V2exCollector(BaseCollector):
    name = "v2ex"

    async def fetch(self) -> list[Item]:
        r = await self.client.get(_URL)
        r.raise_for_status()
        data = r.json()
        items = []
        for i, t in enumerate(data):
            items.append(
                Item(
                    platform=self.name,
                    title=t.get("title", ""),
                    url=t.get("url", ""),
                    rank=i + 1,
                    heat=t.get("replies"),
                )
            )
        return items
