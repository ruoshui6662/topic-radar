"""LLM 客户端：DeepSeek（OpenAI 兼容），统一封装，可换其他服务商。"""
import asyncio
import json
import logging

from openai import AsyncOpenAI

from ..config import settings

logger = logging.getLogger(__name__)


def _client() -> AsyncOpenAI:
    if not settings.deepseek_api_key:
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在 .env 中填写（platform.deepseek.com 获取）")
    return AsyncOpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)


def _parse_json(content: str) -> dict:
    """解析 LLM 返回 JSON：容忍代码围栏与前后杂质。"""
    c = content.strip()
    if c.startswith("```"):
        c = c.split("\n", 1)[1] if "\n" in c else c[3:]
        c = c.rsplit("```", 1)[0].strip()
    start, end = c.find("{"), c.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"LLM 返回中未找到 JSON 对象: {content[:200]}")
    return json.loads(c[start : end + 1])


async def chat_json(system: str, user: str, temperature: float = 0.7) -> dict:
    """调用 LLM 并要求 JSON 输出，带重试（规划 §13：失败重试 + 降级由调用方处理）。"""
    client = _client()
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = await client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or ""
            return _parse_json(content)
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning("LLM 调用失败（第 %d 次）: %s", attempt + 1, e)
            await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"LLM 调用最终失败: {last_err}")
