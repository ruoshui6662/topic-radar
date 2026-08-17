"""B站全站排行：https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all
注意：接口要求带 buvid3 cookie（匿名设备标识），否则风控返回 -352。"""
import uuid

from .base import BaseCollector, Item

_URL = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"


class BilibiliCollector(BaseCollector):
    name = "bilibili"

    def __init__(self, client):
        super().__init__(client)
        # buvid3 只校验存在性，用随机 UUID 即可（实测 test12345 也能通过，UUID 更接近真实）
        self.headers = {"Referer": "https://www.bilibili.com/", "Cookie": f"buvid3={uuid.uuid4().hex[:8]}-{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-infoc"}

    async def fetch(self) -> list[Item]:
        r = await self.client.get(_URL, headers=self.headers)
        r.raise_for_status()
        data = r.json().get("data", {}).get("list", [])
        items = []
        for i, v in enumerate(data):
            items.append(
                Item(
                    platform=self.name,
                    title=v.get("title", ""),
                    url=f"https://www.bilibili.com/video/av{v.get('aid')}",
                    rank=i + 1,
                    heat=(v.get("stat") or {}).get("view"),
                )
            )
        return items
