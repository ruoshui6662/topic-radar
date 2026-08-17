"""话题聚类 v1（关键词级，规划 §6.1）：把跨平台热榜条目聚合为话题。
增量式：只处理 72h 窗口内未归属的条目，匹配活跃话题或新建。"""
import datetime as dt
import logging
import re

import jieba.analyse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..collectors.base import normalize_title
from ..config import settings
from ..db import now_utc
from ..models import HotItem, Topic
from .heat import compute_topic_heat, level_for

logger = logging.getLogger(__name__)

_WORD_RE = re.compile(r"[a-z0-9]{3,}")


def extract_keywords(title: str, topk: int = 6) -> list[str]:
    """关键词提取：中文走 jieba TF-IDF，英文兜底切词。"""
    try:
        tags = jieba.analyse.extract_tags(title or "", topK=topk)
        if tags:
            return [t.lower() for t in tags]
    except Exception:  # noqa: BLE001 jieba 偶发失败不阻断聚类
        logger.warning("jieba 关键词提取失败: %r", title, exc_info=True)
    words = [w for w in _WORD_RE.findall((title or "").lower())]
    return words[:topk]


def _sim(kws_a: set[str], kws_b: set[str]) -> float:
    if not kws_a or not kws_b:
        return 0.0
    inter = len(kws_a & kws_b)
    return inter / len(kws_a | kws_b)


def refresh_topic_stats(session: Session, topic_id: int) -> None:
    """按话题下的条目重算统计，并更新热度分。"""
    row = session.execute(
        select(
            func.count(HotItem.id),
            func.count(func.distinct(HotItem.platform)),
            func.min(HotItem.rank),
            func.max(HotItem.captured_at),
        ).where(HotItem.topic_id == topic_id)
    ).one()
    topic = session.get(Topic, topic_id)
    if topic is None:
        return
    topic.item_count, topic.platform_count, topic.best_rank, topic.last_seen_at = (
        row[0] or 0, row[1] or 0, row[2] or None, row[3] or topic.last_seen_at,
    )
    topic.heat_score = compute_topic_heat(topic)
    topic.heat_level = level_for(topic.heat_score)


def run_clustering(session: Session) -> dict:
    """增量聚类，返回 {assigned: n, created: n}。"""
    now = now_utc()
    cutoff = now - dt.timedelta(hours=settings.cluster_window_hours)

    items = session.execute(
        select(HotItem)
        .where(HotItem.captured_at >= cutoff, HotItem.topic_id.is_(None))
        .order_by(HotItem.captured_at.asc())
    ).scalars().all()
    if not items:
        return {"assigned": 0, "created": 0}

    active_topics = session.execute(
        select(Topic).where(Topic.status == "active", Topic.last_seen_at >= cutoff)
    ).scalars().all()
    # 活跃话题特征：(topic, 关键词集合, 代表标题归一化)
    topic_features = [(t, set(t.keywords or []), normalize_title(t.title)) for t in active_topics]

    assigned = created = 0
    touched: set[int] = set()
    for item in items:
        kws = set(extract_keywords(item.title))
        norm = item.title_norm

        best_topic, best_sim = None, 0.0
        for t, t_kws, t_norm in topic_features:
            s = _sim(kws, t_kws)
            # 标题归一化完全一致 = 同一话题（跨平台转载常见）
            if norm and norm == t_norm:
                s = 1.0
            if s > best_sim:
                best_topic, best_sim = t, s

        if best_topic and best_sim >= settings.cluster_sim_threshold:
            item.topic_id = best_topic.id
            assigned += 1
            # 合并关键词（上限 15 个，保持特征稳定）
            merged = list(dict.fromkeys(list(best_topic.keywords) + sorted(kws)))
            best_topic.keywords = merged[:15]
            best_topic.last_seen_at = now
            touched.add(best_topic.id)
        else:
            topic = Topic(
                title=item.title,
                keywords=sorted(kws)[:10],
                first_seen_at=item.captured_at,
                last_seen_at=now,
                status="active",
            )
            session.add(topic)
            session.flush()
            item.topic_id = topic.id
            created += 1
            topic_features.append((topic, kws, norm))
            touched.add(topic.id)

    for tid in touched:
        refresh_topic_stats(session, tid)
    session.commit()
    return {"assigned": assigned, "created": created}
