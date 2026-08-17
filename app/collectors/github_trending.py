"""GitHub Trending：解析 https://github.com/trending 页面（实测可用）。"""
from bs4 import BeautifulSoup

from .base import BaseCollector, Item

_URL = "https://github.com/trending?since=daily"


class GithubTrendingCollector(BaseCollector):
    name = "github"

    async def fetch(self) -> list[Item]:
        r = await self.client.get(_URL)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        items = []
        for i, a in enumerate(soup.select("article.Box-row")):
            link = a.select_one("h2 a")
            full_name = (link.get("href") or "").strip("/") if link else ""
            desc_el = a.select_one("p")
            stars_el = a.select_one("#repo-stars-counter-star")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            title = f"{full_name}: {desc}" if desc else full_name
            heat = None
            if stars_el:
                try:
                    heat = float(stars_el.get_text(strip=True).replace(",", ""))
                except ValueError:
                    heat = None
            items.append(
                Item(
                    platform=self.name,
                    title=title,
                    url=f"https://github.com/{full_name}",
                    rank=i + 1,
                    heat=heat,
                )
            )
        return items
