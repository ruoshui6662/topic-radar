"""通用 RSS 采集器：IT之家、少数派等行业信源（实测可用）。"""
import feedparser

from .base import BaseCollector, Item


class RssCollector(BaseCollector):
    def __init__(self, client, name: str, feed_url: str, max_items: int = 30):
        super().__init__(client)
        self.name = name
        self.feed_url = feed_url
        self.max_items = max_items

    async def fetch(self) -> list[Item]:
        r = await self.client.get(self.feed_url)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
        items = []
        for i, e in enumerate(feed.entries[: self.max_items]):
            items.append(
                Item(
                    platform=self.name,
                    title=e.get("title", ""),
                    url=e.get("link", ""),
                    rank=i + 1,
                    extra={"published": e.get("published", "")},
                )
            )
        return items
