"""每日选题日报生成（规划 §7.3 + §16 样例选题卡格式）。
流程：取热度 Top N 话题 → 分块并行调 DeepSeek/网关 评估 → 选题卡 → Markdown 日报入库。"""
import asyncio
import datetime as dt
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import now_utc
from ..models import Report, Topic
from .client import chat_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是资深科技/AI 领域公众号主编，深谙"10万+"爆款逻辑。根据给定的话题热度数据，结合公众号运营经验，为科技/AI 类公众号生成选题建议。

严格输出 JSON，格式如下：
{"selections": [
  {"topic": "话题名", "heat_score": 92.0, "heat_level": "S", "value_score": 85, "grade": "S",
   "reason": "为什么适合本账号（匹配度+竞争度+时效窗口，2-3句话）",
   "directions": ["写作方向1", "写作方向2", "写作方向3"],
   "advice": "写作建议（结构/节奏/数据点，1-2句话）",
   "titles": ["标题1", "标题2", "标题3"]}
]}

规则：
1. grade 为 S/A/B/C 四级；heat_level 为 B 及以下的话题最多给 A 级，除非与科技/AI 领域强相关。
2. 标题必须"10万加"级别：制造悬念、冲突感或好奇心缺口，带具体数字或强对比，避免平铺直叙。
   参考钩子：「别急着xxx！」「xxx背后，藏着xxx」「实测xxx，颠覆预期」「xxx翻车了？」「xxx深度拆解」「xxx的真相，藏不住了」「xxx vs xxx，差距有多大」。
   3 条标题用不同钩子，不要同质化。
3. 写作方向要给差异化角度：避开头部大号已写烂的角度（如泛泛的"发布啦"），找解读、实测、对比、影响、避坑等具体切入点。
4. 写作建议要可执行：开头 300 字怎么抓人、放几个数据点、结构怎么排、怎么引导在看/转发。
5. 所有话题都要输出，不要遗漏；value_score 是 0-100 的整数；所有字段用中文。"""


async def build_report(session: Session, report_date: dt.date) -> Report:
    """生成并入库日报，返回 Report 对象。"""
    cutoff = now_utc() - dt.timedelta(hours=48)
    topics = session.execute(
        select(Topic)
        .where(Topic.status == "active", Topic.last_seen_at >= cutoff)
        .order_by(Topic.heat_score.desc())
        .limit(settings.top_n_topics)
    ).scalars().all()
    if not topics:
        raise RuntimeError("没有可评估的话题：请先运行采集与聚类（python -m app.scripts.collect_once）")

    data = [
        {
            "title": t.title,
            "heat_score": t.heat_score,
            "heat_level": t.heat_level,
            "platforms": t.platform_count,
            "items": t.item_count,
            "best_rank": t.best_rank,
            "keywords": t.keywords,
        }
        for t in topics
    ]

    # 分块并行评估：单块更快、更稳，一块失败不拖垮整体
    chunk_size = settings.llm_chunk_size
    chunks = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
    logger.info("日报评估 %d 个话题，分 %d 块并行", len(data), len(chunks))
    results = await asyncio.gather(
        *(
            chat_json(SYSTEM_PROMPT, f"话题数据（JSON）：\n{json.dumps(chunk, ensure_ascii=False)}", temperature=0.7)
            for chunk in chunks
        ),
        return_exceptions=True,
    )
    selections: list[dict] = []
    for i, r in enumerate(results):
        if isinstance(r, BaseException):
            logger.error("第 %d 块评估失败: %s", i + 1, r)
            continue
        selections.extend(r.get("selections") or [])
    if not selections:
        raise RuntimeError("LLM 评估全部失败，无法生成日报")
    logger.info("评估完成，共 %d 个选题卡", len(selections))
    md = render_markdown(report_date, selections)

    report = session.execute(select(Report).where(Report.report_date == report_date)).scalars().first()
    if report:
        report.content_md = md
        report.selections_json = selections
    else:
        report = Report(report_date=report_date, content_md=md, selections_json=selections)
        session.add(report)
    session.commit()
    return report


def render_markdown(report_date: dt.date, selections: list[dict]) -> str:
    """选题卡 → 飞书可用的 Markdown（S 级详细、A 级精简）。"""
    s_list = [s for s in selections if s.get("grade") == "S"]
    a_list = [s for s in selections if s.get("grade") == "A"]
    lines = [f"# 📊 今日选题日报 {report_date}", ""]

    if not selections:
        lines.append("今日无可评估的热点话题，建议先观察积累。")
        return "\n".join(lines)

    lines.append(f"**共 {len(selections)} 个候选 · S 级 {len(s_list)} · A 级 {len(a_list)}**")
    lines.append("")

    def card(s: dict, detail: bool) -> str:
        grade = s.get("grade", "C")
        heat = s.get("heat_score", 0)
        block = [f"**【{grade}级】** {s.get('topic', '')} ｜ 热度 {heat} 分 ｜ 价值 {s.get('value_score', '-')} 分"]
        if detail:
            block.append(f"   📌 理由：{s.get('reason', '')}")
            block.append(f"   ✍️ 方向：{'；'.join(s.get('directions', []))}")
            block.append(f"   💡 建议：{s.get('advice', '')}")
            block.append(f"   🏷 标题候选：")
            for t in s.get("titles", [])[:3]:
                block.append(f"      · {t}")
        return "\n".join(block)

    for s in s_list:
        lines.append(card(s, detail=True))
        lines.append("")
    for s in a_list:
        lines.append(card(s, detail=False))
        lines.append("")
    lines.append("---")
    lines.append("数据为跨平台热度代理指标（非真实阅读量）· 详见工作台（M3 上线）")
    return "\n".join(lines)
