# 微信公众号选题工作台

自动化选题决策系统：多平台热点采集 → 话题聚类 → 热度评分 → LLM 选题评估 → 每日飞书推送。
技术方案见 [技术规划.md](技术规划.md)（v0.4）。

## 目录结构

```
app/
├── collectors/   采集层（8 个平台适配器 + 注册表，单源失败不影响整体）
├── processors/   量化层（话题聚类 v1 + 热度评分）
├── llm/          LLM 层（DeepSeek 客户端 + 日报生成）
├── push/         分发层（飞书 webhook）
├── scripts/      命令行脚本（init_db / collect_once / make_report / push_test）
├── config.py     配置（env 驱动）
├── db.py / models.py
├── scheduler.py  定时任务（采集 30min / 聚类 2h / 日报 7:30 / 推送 8:00）
└── main.py       FastAPI 入口（健康检查 + 手动触发）
deploy/           NAS 部署脚本（build-push.sh / deploy.sh / wewe-rss.md）
docker-compose.yml（NAS 编排）
```

## 本地开发（Windows / macOS）

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Mac/Linux 用 .venv/bin/python
cp .env.example .env                                          # 填写 DEEPSEEK_API_KEY / FEISHU_WEBHOOK_URL
python -m app.scripts.init_db          # 建表
python -m app.scripts.collect_once     # 采集+聚类+Top 话题
python -m app.scripts.make_report      # 生成今日日报（Markdown，不推送）
python -m app.scripts.push_test        # 飞书连通性测试
python -m app.main                     # 启动服务 http://localhost:8000/health
```

## NAS 部署

1. 构建镜像并推送 GHCR：`GITHUB_USER=xxx ./deploy/build-push.sh`（需 gh 登录）
2. NAS 建目录，上传 compose 与 .env：`NAS_USER=xx NAS_HOST=192.168.1.x ./deploy/deploy.sh`
3. 验证：`http://<NAS_IP>:8000/health`

## M1 验收标准（技术规划 §14）

- [ ] 热榜采集连续 7 天无中断（/health 看各源最近采集时间）
- [ ] 每日话题 ≥30 个
- [ ] 日报连续 3 天无人工干预自动发出
- [ ] 用户对 S/A 级选题与自身直觉一致性 ≥70%
- [ ] wewe-rss spike 出结论（Go/No-Go）

## 数据源现状（2026-08-17 实测）

| 源 | 状态 | 说明 |
|---|---|---|
| 百度热搜 / B站 / 头条 / HN / V2EX / GitHub / IT之家 / 少数派 | ✅ 可用 | 直连 |
| 微博 / 知乎 / 抖音 | ⏸ 本机被拦截 | 待 NAS tophub 容器补充 |
