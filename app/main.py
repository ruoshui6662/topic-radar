"""FastAPI 入口：M1 提供轻量 Web 页面 + 健康检查 + 手动触发接口，M3 挂完整工作台。"""
import asyncio
import datetime as dt
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="选题工作台", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index():
    """轻量版工作台页面（M3 前使用）。"""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health():
    """各数据源最近一次采集状态（验收用：连续采集无中断）。"""
    from .models import HotItem
    session = SessionLocal()
    try:
        rows = session.execute(
            select(HotItem.platform, HotItem.captured_at)
            .distinct(HotItem.platform)
        ).scalars().all()
        # 简化：按平台取最新 captured_at
        latest = {}
        for p in rows:
            t = session.execute(
                select(HotItem.captured_at)
                .where(HotItem.platform == p)
                .order_by(HotItem.captured_at.desc())
            ).scalars().first()
            latest[p] = t.isoformat() if t else None
        return {"status": "ok", "scheduler": "running", "last_collect": latest}
    finally:
        session.close()


@app.post("/api/trigger/collect")
async def trigger_collect():
    from .collectors.registry import run_all
    from .processors.cluster import run_clustering
    session = SessionLocal()
    try:
        results = await run_all()
        cluster = await asyncio.to_thread(run_clustering, session)
        return {"collect": results, "cluster": cluster}
    except Exception as e:  # noqa: BLE001 页面友好展示错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    finally:
        session.close()


@app.post("/api/trigger/report")
async def trigger_report():
    from .llm.report import build_report
    session = SessionLocal()
    try:
        report = await build_report(session, dt.date.today())
        return {"report_date": report.report_date.isoformat(), "topics": len(report.selections_json)}
    except Exception as e:  # noqa: BLE001 页面友好展示错误
        return JSONResponse(status_code=400, content={"error": str(e)})
    finally:
        session.close()


@app.get("/api/topics")
async def list_topics(limit: int = 20):
    from .models import Topic
    session = SessionLocal()
    try:
        rows = session.execute(
            select(Topic)
            .where(Topic.status == "active")
            .order_by(Topic.heat_score.desc())
            .limit(limit)
        ).scalars().all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "heat_score": t.heat_score,
                "heat_level": t.heat_level,
                "platforms": t.platform_count,
                "items": t.item_count,
                "first_seen": t.first_seen_at.isoformat(),
            }
            for t in rows
        ]
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
