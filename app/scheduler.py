"""定时调度（规划 §13）：热榜采集 30min、聚类 2h、日报生成 7:30、推送 8:00。"""
import datetime as dt
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .config import settings
from .db import SessionLocal
from .collectors.registry import run_all
from .llm.report import build_report
from .push.feishu import send_markdown

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.tz)


def _job_collect() -> None:
    import asyncio
    try:
        results = asyncio.run(run_all())
        ok = [k for k, v in results.items() if not v.startswith("FAIL")]
        logger.info("采集完成: %s / %s 成功 %s", len(ok), len(results), results)
    except Exception:  # noqa: BLE001
        logger.exception("采集任务失败")


def _job_cluster() -> None:
    import asyncio
    from .processors.cluster import run_clustering
    session = SessionLocal()
    try:
        result = asyncio.run(asyncio.to_thread(run_clustering, session))
        logger.info("聚类完成: %s", result)
    finally:
        session.close()


def _job_report() -> None:
    import asyncio
    session = SessionLocal()
    try:
        report = asyncio.run(build_report(session, dt.date.today()))
        logger.info("日报生成完成: %s", report.report_date)
    except Exception:  # noqa: BLE001
        logger.exception("日报生成失败")
    finally:
        session.close()


def _job_push() -> None:
    import asyncio
    session = SessionLocal()
    try:
        from sqlalchemy import select
        from .models import Report
        report = session.execute(
            select(Report).where(Report.report_date == dt.date.today())
        ).scalars().first()
        if report is None:
            logger.warning("今日无日报可推送（先跑日报生成任务）")
            return
        ok = asyncio.run(send_markdown(f"📊 今日选题日报 {report.report_date}", report.content_md))
        if ok:
            from .db import now_utc
            report.pushed_at = now_utc()
            session.commit()
            logger.info("日报已推送")
    finally:
        session.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(_job_collect, IntervalTrigger(minutes=settings.collect_interval_min), id="collect", replace_existing=True)
    scheduler.add_job(_job_cluster, IntervalTrigger(hours=2), id="cluster", replace_existing=True)
    scheduler.add_job(_job_report, CronTrigger(hour=settings.report_hour, minute=settings.report_minute), id="report", replace_existing=True)
    scheduler.add_job(_job_push, CronTrigger(hour=settings.push_hour, minute=settings.push_minute), id="push", replace_existing=True)
    scheduler.start()
    logger.info("调度器已启动（时区 %s）", settings.tz)
