"""热度评分（规划 §6.2 代理指标体系，v1 版本）：
话题热度 = [w1·跨平台覆盖 + w2·条目量 + w3·最佳位次] × 时间衰减
权重来自 settings.heat_weights（先验值，M3 工作台可视化微调）。"""
import math

from ..config import settings
from ..db import now_utc
from ..models import Topic


def compute_topic_heat(topic: Topic) -> float:
    w = settings.heat_weights
    plats = min(topic.platform_count or 0, 5)
    vol = min(topic.item_count or 0, 50)
    rank = topic.best_rank or 100

    base = (
        w["platforms"] * math.tanh(plats / 3)
        + w["volume"] * math.tanh(math.log1p(vol) / 4)
        + w["rank"] * (1 - min(rank, 50) / 50)
    )
    hours = max((now_utc() - topic.first_seen_at).total_seconds() / 3600, 0.001)
    freshness = math.exp(-hours / settings.heat_decay_hours)
    return round(100 * base * freshness, 1)


def level_for(score: float) -> str:
    thresholds = settings.heat_thresholds
    for lvl in ("S", "A", "B"):
        if score >= thresholds[lvl]:
            return lvl
    return "C"
