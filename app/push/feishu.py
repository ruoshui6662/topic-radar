"""推送层（规划 §12）：飞书自定义机器人 webhook。adapter 可插拔，后续可加企业微信等。"""
import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


async def send_markdown(title: str, markdown: str, webhook: str | None = None) -> bool:
    """发送飞书交互卡片（lark_md）。成功返回 True。"""
    webhook = webhook or settings.feishu_webhook_url
    if not webhook:
        raise RuntimeError("未配置 FEISHU_WEBHOOK_URL，请在 .env 中填写（飞书群 → 群机器人 → 自定义机器人）")

    card = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": markdown}}],
        },
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(webhook, json=card)
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            logger.error("飞书推送失败: %s", data)
            return False
        return True
