"""采集器注册表：并发跑全部源，单源失败不影响整体（v0.4 规划 §5.1 多源冗余）。"""
import asyncio
import logging

import httpx
from sqlalchemy.orm import Session

from ..db import SessionLocal
from .base import DEFAULT_HEADERS, BaseCollector, save_items
from .baidu import BaiduCollector
from .bilibili import BilibiliCollector
from .github_trending import GithubTrendingCollector
from .hn import HNCollector
from .rss_generic import RssCollector
from .toutiao import ToutiaoCollector
from .v2ex import V2exCollector

logger = logging.getLogger(__name__)


def build_collectors(client: httpx.AsyncClient) -> list[BaseCollector]:
    return [
        BaiduCollector(client),
        BilibiliCollector(client),
        ToutiaoCollector(client),
        HNCollector(client),
        V2exCollector(client),
        GithubTrendingCollector(client),
        RssCollector(client, "ithome", "https://www.ithome.com/rss/"),
        RssCollector(client, "sspai", "https://sspai.com/feed"),
    ]


async def run_all() -> dict[str, str]:
    """执行全部采集并入库。返回 {平台: 结果}，失败平台以 FAIL 开头。"""
    async with httpx.AsyncClient(
        timeout=20, headers=DEFAULT_HEADERS, follow_redirects=True
    ) as client:
        collectors = build_collectors(client)
        outputs = await asyncio.gather(
            *(c.fetch() for c in collectors), return_exceptions=True
        )

    results: dict[str, str] = {}
    session: Session = SessionLocal()
    try:
        for c, out in zip(collectors, outputs):
            if isinstance(out, Exception):
                results[c.name] = f"FAIL: {type(out).__name__}: {out}"
                logger.warning("[collector:%s] 失败: %s", c.name, out)
                continue
            try:
                inserted = save_items(session, c.name, out)
                results[c.name] = f"OK(+{inserted})"
            except Exception as e:  # noqa: BLE001 单源入库失败不阻断整体
                session.rollback()
                results[c.name] = f"FAIL(入库): {e}"
                logger.exception("[collector:%s] 入库失败", c.name)
        session.commit()
    finally:
        session.close()
    return results
