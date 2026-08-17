"""百度热搜：https://top.baidu.com/api/board?platform=wise&tab=realtime（实测可用）"""
from .base import BaseCollector, Item

_URL = "https://top.baidu.com/api/board?platform=wise&tab=realtime"


class BaiduCollector(BaseCollector):
    name = "baidu"

    async def fetch(self) -> list[Item]:
        r = await self.client.get(_URL)
        r.raise_for_status()
        data = r.json().get("data", {})

        def walk(node, out):
            """递归收集含 word 字段的条目，兼容接口结构变化。"""
            if isinstance(node, dict):
                if "word" in node and isinstance(node.get("word"), str) and node["word"]:
                    out.append(node)
                for v in node.values():
                    walk(v, out)
            elif isinstance(node, list):
                for v in node:
                    walk(v, out)

        entries: list[dict] = []
        walk(data, entries)
        items = []
        for i, e in enumerate(entries):
            items.append(
                Item(
                    platform=self.name,
                    title=e.get("word", ""),
                    url=e.get("url", "") or e.get("rawUrl", ""),
                    rank=i + 1,
                    heat=e.get("hotScore"),
                )
            )
        return items
