"""手动跑一次「采集 + 聚类 + Top 话题」全流程。用法：python -m app.scripts.collect_once"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.collectors.registry import run_all  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Topic  # noqa: E402
from app.processors.cluster import run_clustering  # noqa: E402


async def main() -> None:
    print("== ① 采集 ==")
    results = await run_all()
    for name, res in results.items():
        print(f"  {name:<12} {res}")

    session = SessionLocal()
    try:
        print("\n== ② 聚类 ==")
        print(f"  {run_clustering(session)}")

        print("\n== ③ Top 话题 ==")
        topics = session.execute(
            select(Topic)
            .where(Topic.status == "active")
            .order_by(Topic.heat_score.desc())
            .limit(15)
        ).scalars().all()
        if not topics:
            print("  （暂无话题）")
        for t in topics:
            print(f"  [{t.heat_level}] {t.heat_score:5.1f}  {t.title[:44]:<44} {t.platform_count}平台/{t.item_count}条")
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
