"""初始化数据库表（M1 起即建全量 schema，M2/M3 直接使用）。用法：python -m app.scripts.init_db"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

(ROOT / "data").mkdir(exist_ok=True)

from app import models  # noqa: F401 注册所有模型
from app.db import Base, engine

Base.metadata.create_all(engine)
print(f"✅ 数据表已创建: {engine.url}")
