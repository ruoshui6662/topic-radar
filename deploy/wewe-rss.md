# wewe-rss 部署与 spike 验证指南（M1 第 1 周）

目标：在 **NAS** 上用 wewe-rss 订阅 3 个公众号，验证「公众号 → RSS → 入库」链路可用性（3 天），
M1 末做 Go/No-Go 决策（技术规划 §5.4 / P0-3）。

## 前置条件（合规红线）

- **必须用独立的微信小号**（从未用于公众号运营、无重要数据的号），微信读书绑定该小号。
  绝不用日常主号 —— wewe-rss 借用微信读书凭证，存在账号限制风险（技术规划 §5.4）。
- NAS 可访问 Docker。

## 1. 部署（NAS 上执行）

在 NAS 的 `/docker/wewe-rss/` 下新建 `docker-compose.yml`：

```yaml
services:
  mongo:
    image: mongo:7
    restart: unless-stopped
    volumes: ["./data/mongo:/data/db"]

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  wewe-rss:
    image: cooderl/wewe-rss:latest   # 已核实：镜像存在且活跃（amd64/arm64）
    restart: unless-stopped
    depends_on: [mongo, redis]
    ports: ["4000:4000"]
    environment:
      DATABASE_URL: mongodb://mongo:27017/wewe-rss
      AUTH_CODE: "换成你自己的登录口令"   # 登录界面要填
      MAX_REQUEST_PER_MINUTE: 60
      FEED_MODE: "fulltext"
      TZ: Asia/Shanghai
    volumes: ["./data/wewe-rss:/app/data"]

  # ② 若要自动生成 RSS 配置（可选）
  # wewe-rss-agg:
  #   image: cooderl/wewe-rss-agg
  #   ...
```

启动：

```bash
docker compose up -d
# 浏览器打开 http://<NAS_IP>:4000 ，输入 AUTH_CODE 登录
```

## 2. 登录微信读书并添加订阅（手动，一次性）

1. 小号手机装「微信读书」，登录该小号
2. 微信读书中搜索并关注 3 个测试公众号（建议：量子位、机器之心、少数派）
3. wewe-rss 界面：「公众号订阅」→ 扫码/授权（微信读书网页版登录）→ 自动导入已关注的公众号
4. wewe-rss 会为每个账号生成 RSS 地址（`/feed/...`）

## 3. 验证（spike 验收标准）

- [ ] wewe-rss 界面能看到 3 个账号的最近文章（标题/正文/链接）
- [ ] RSS 地址在浏览器可打开，返回 XML
- [ ] 运行 24h 后，新增文章能出现在 RSS 中（定时抓取生效）
- [ ] 采集器接入：在 app 的 .env 中加 `WEWE_RSS_URLS=...`（M2 开发，spike 阶段人工确认即可）

## 4. Go / No-Go 判断

| 结论 | 条件 |
|---|---|
| **Go** | 3 个账号 RSS 稳定输出 ≥48h，文章有正文，账号无异常提示 |
| **No-Go** | 登录失败 / RSS 空 / 小号被限制 / 频繁验证码 → 启用预案（gewechat 协议机器人 / RSSHub / 手动导入），并同步更新技术规划 |

## 5. 风险控制

- 抓取频率不高于 1 次/小时（MAX_REQUEST_PER_MINUTE 已限）
- 小号不用来聊天/加群，降低风控概率
- 若小号异常：立即停止服务，用另一小号重试（多号轮换）
