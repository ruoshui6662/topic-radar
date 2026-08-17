"""全局配置：env 驱动，默认值适配本地开发（SQLite + 直连热榜 API）。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 数据库（本地 SQLite / NAS Postgres）
    database_url: str = "sqlite:///./data/workbench.db"

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 飞书推送
    feishu_webhook_url: str = ""

    # 调度（本地时间，TZ 见 tz 字段）
    collect_interval_min: int = 30
    report_hour: int = 7
    report_minute: int = 30
    push_hour: int = 8
    push_minute: int = 0
    top_n_topics: int = 15
    tz: str = "Asia/Shanghai"

    # ---- 热度评分权重（先验值，P0-2 修订：先验 + 人工微调，M3 工作台可视化拖拽）----
    heat_weights: dict = {
        "platforms": 0.40,   # 跨平台覆盖度
        "volume": 0.30,      # 条目量（log 归一）
        "rank": 0.30,        # 最佳位次
    }
    heat_decay_hours: float = 12.0   # 时间衰减半衰期
    heat_thresholds: dict = {"S": 80.0, "A": 60.0, "B": 40.0}

    # 聚类参数（v1 关键词级）
    cluster_sim_threshold: float = 0.25   # 关键词 Jaccard 相似度阈值
    cluster_window_hours: int = 72        # 活跃话题窗口


settings = Settings()
