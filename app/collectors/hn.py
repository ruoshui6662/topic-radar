"""Hacker News：Firebase 公开 API（实测可用），取 top50。"""
import asyncio

from .base import BaseCollector, Item

_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


class HNCollector(BaseCollector):
    name = "hackernews"

    async def fetch(self) -> list[Item]:
        ids = (await self.client.get(_TOP_URL)).json()[:50]
        responses = await asyncio.gather(
            *(self.client.get(_ITEM_URL.format(i)) for i in ids)
        )
        items = []
        rank = 0
        for r in responses:
            v = r.json()
            if not v or not v.get("title"):
                continue
            rank += 1
            items.append(
                Item(
                    platform=self.name,
                    title=v.get("title", ""),
                    url=v.get("url") or f"https://news.ycombinator.com/item?id={v.get('id')}",
                    rank=rank,
                    heat=v.get("score"),
                )
            )
        return items
