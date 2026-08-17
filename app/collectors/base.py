"""采集层基础：归一化条目、标题归一化、入库去重。"""
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import now_utc
from ..models import HotItem

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 归一化时要去掉的括号/分隔符
_BRACKET_RE = re.compile(r"[（(【\[](.{0,20}?)[)）】\]]")
_SEP_RE = re.compile(r"[\[\]()（）{}<>《》「」『』\"'“”‘’·,，。;；:：!！?？|｜\s\-—_~]+")
_PLATFORM_SUFFIXES = ("知乎热榜", "百度热搜", "微博热搜", "实时更新", "热搜榜", "今日头条", "哔哩哔哩")


@dataclass
class Item:
    """归一化后的热榜条目（跨平台统一结构）"""
    platform: str
    title: str
    url: str
    rank: int
    heat: float | None = None
    extra: dict = field(default_factory=dict)


def normalize_title(title: str) -> str:
    """标题归一化：全角→半角、去括号内容（栏目/来源）、去分隔符与平台后缀，用于去重与聚类。"""
    t = unicodedata.normalize("NFKC", title or "").lower()
    t = _BRACKET_RE.sub("", t)
    t = _SEP_RE.sub("", t)
    for suf in _PLATFORM_SUFFIXES:
        t = t.replace(suf, "")
    return t.strip()


class BaseCollector(ABC):
    """平台采集器抽象：每个平台一个子类，接口变动只改一个文件。"""

    name: str = "base"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @abstractmethod
    async def fetch(self) -> list[Item]:
        """抓取并归一化热榜条目（按位次升序）。"""


def save_items(session: Session, platform: str, items: list[Item]) -> int:
    """入库：同平台+归一化标题 72h 内已存在则更新位次/热度，否则插入。返回本次插入数。"""
    now = now_utc()
    seen: dict[str, Item] = {}
    for it in items:
        norm = normalize_title(it.title)
        if not norm or norm in seen:
            continue
        seen[norm] = it

    inserted = 0
    for norm, it in seen.items():
        existing = session.execute(
            select(HotItem)
            .where(HotItem.platform == platform, HotItem.title_norm == norm)
            .order_by(HotItem.captured_at.desc())
        ).scalars().first()
        if existing and (now - existing.captured_at).total_seconds() < 72 * 3600:
            existing.rank = it.rank
            existing.heat = it.heat
            existing.url = it.url or existing.url
            existing.captured_at = now
        else:
            session.add(
                HotItem(
                    platform=platform,
                    title=it.title,
                    title_norm=norm,
                    url=it.url,
                    rank=it.rank,
                    heat=it.heat,
                    extra=it.extra,
                    captured_at=now,
                )
            )
            inserted += 1
    return inserted
