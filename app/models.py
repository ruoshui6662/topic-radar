"""数据模型（v0.4 规划 §11）。M1 用到：hot_items / topics / reports；
其余表（articles/selections/feedback/calibration 等）先建好，M2/M3 直接使用，避免迁移。"""
import datetime as dt
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now_utc


class HotItem(Base):
    """热榜条目（各平台原始信号）"""
    __tablename__ = "hot_items"
    __table_args__ = (UniqueConstraint("platform", "title_norm", name="uq_platform_title"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    title_norm: Mapped[str] = mapped_column(String(255), index=True)  # 归一化标题，用于去重/聚类
    url: Mapped[str] = mapped_column(String(512), default="")
    rank: Mapped[int] = mapped_column(Integer, default=0)
    heat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 平台原始热度值
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    captured_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc, index=True)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id"), nullable=True, index=True)


class Topic(Base):
    """话题（跨平台聚类结果）"""
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))           # 代表标题（最早条目）
    keywords: Mapped[list] = mapped_column(JSON, default=list)  # 累计关键词包
    first_seen_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc, index=True)
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc, index=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    platform_count: Mapped[int] = mapped_column(Integer, default=0)
    best_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heat_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heat_level: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")


class Report(Base):
    """每日选题日报"""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_date: Mapped[dt.date] = mapped_column(Date, unique=True, index=True)
    content_md: Mapped[str] = mapped_column(Text, default="")     # 飞书/展示用 Markdown
    selections_json: Mapped[list] = mapped_column(JSON, default=list)  # LLM 选题卡原始数据
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)
    pushed_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)


# ---------------- M2 起使用 ----------------

class Account(Base):
    """公众号账号（wewe-rss 内容流）"""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    biz_id: Mapped[str] = mapped_column(String(64), default="")
    category: Mapped[str] = mapped_column(String(64), default="")
    level: Mapped[str] = mapped_column(String(16), default="")
    follow_count_est: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")


class Article(Base):
    """公众号文章（内容流）"""
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(512), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), default="", index=True)
    publish_time: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="wewe-rss")


class TopicArticle(Base):
    """话题-文章关联（M2）"""
    __tablename__ = "topic_articles"
    __table_args__ = (UniqueConstraint("topic_id", "article_id", name="uq_topic_article"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))


class Selection(Base):
    """选题（LLM 评估结果）"""
    __tablename__ = "selections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id"), nullable=True)
    grade: Mapped[str] = mapped_column(String(4), default="C")
    value_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    direction: Mapped[list] = mapped_column(JSON, default=list)   # 写作方向
    advice: Mapped[str] = mapped_column(Text, default="")         # 写作建议
    titles: Mapped[list] = mapped_column(JSON, default=list)      # 标题候选
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/采纳/发布
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)


class Profile(Base):
    """账号画像（用户维护，M3 可视化编辑）"""
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)


class Feedback(Base):
    """自己文章发布后的真实数据回填"""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    selection_id: Mapped[Optional[int]] = mapped_column(ForeignKey("selections.id"), nullable=True)
    article_id: Mapped[Optional[int]] = mapped_column(ForeignKey("articles.id"), nullable=True)
    reads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fans_delta: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    published_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)


class Calibration(Base):
    """外部基准校验（每周抽查真实阅读量，标定代理指标）"""
    __tablename__ = "calibration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[Optional[int]] = mapped_column(ForeignKey("topics.id"), nullable=True)
    checked_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)
    real_reads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    real_likes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    real_shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(String(255), default="")


class ChatLog(Base):
    """对话问答日志（M3）"""
    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    tool_used: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=now_utc)
