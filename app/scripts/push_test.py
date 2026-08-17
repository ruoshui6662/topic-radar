"""飞书推送连通性测试。用法：python -m app.scripts.push_test"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.push.feishu import send_markdown  # noqa: E402


async def main() -> None:
    ok = await send_markdown("✅ 选题工作台测试", "**连接成功**\n这是来自选题工作台的测试消息。")
    print("✅ 推送成功" if ok else "❌ 推送失败，请检查 FEISHU_WEBHOOK_URL")


if __name__ == "__main__":
    asyncio.run(main())
