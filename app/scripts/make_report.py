"""生成今日日报（不推送），Markdown 存 data/reports/。用于样例共创，先看内容再接线推送。
用法：python -m app.scripts.make_report [YYYY-MM-DD]"""
import asyncio
import datetime as dt
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from app.db import SessionLocal  # noqa: E402
from app.llm.report import build_report  # noqa: E402


async def main() -> None:
    date = dt.date.today()
    if len(sys.argv) > 1:
        date = dt.date.fromisoformat(sys.argv[1])

    logging.info("开始生成日报 %s（LLM 评估中，请稍候…）", date)
    session = SessionLocal()
    try:
        report = await build_report(session, date)
        out_dir = ROOT / "data" / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{date.isoformat()}.md"
        out.write_text(report.content_md, encoding="utf-8")
        print(f"✅ 日报已生成: {out}")
        print("---- 内容预览 ----")
        print(report.content_md)
    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
