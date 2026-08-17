"""今日头条热榜：https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc（实测可用）"""
from .base import BaseCollector, Item

_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"


class ToutiaoCollector(BaseCollector):
    name = "toutiao"

    async def fetch(self) -> list[Item]:
        r = await self.client.get(_URL)
        r.raise_for_status()
        data = r.json().get("data", [])
        items = []
        for i, e in enumerate(data):
            cluster_id = e.get("ClusterId")
            url = e.get("Url") or (f"https://www.toutiao.com/trending/{cluster_id}/" if cluster_id else "")
            items.append(
                Item(
                    platform=self.name,
                    title=e.get("Title", ""),
                    url=url,
                    rank=i + 1,
                    heat=e.get("HotValue"),
                )
            )
        return items
