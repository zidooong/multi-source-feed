# Multi-Source Feed 📡

AI-curated daily tech brief from customizable sources, delivered via your preferred messaging channel.

AI 驱动的每日科技简报，聚合多个可配置信息源，通过你配置的消息通道推送。

```
Your Sources → Fetch → Dedup → LLM Memo → Daily Brief (5 sections)
```

---

## Setup / 安装

> **Prerequisites / 前提条件:** Python 3.9+, [OpenClaw](https://openclaw.ai), a messaging channel (Telegram, Discord, Feishu, etc.)

### Step 1 — Install / 安装

```bash
git clone https://github.com/zidooong/multi-source-feed.git && cd multi-source-feed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
```

### Step 2 — API Keys / 配置密钥

```bash
cp .env.example .env
# Fill in TAVILY_API_KEY (free: https://tavily.com)
# Fill in PRODUCTHUNT_API_TOKEN (free: https://api.producthunt.com/v2/docs)
```

### Step 3 — X/Twitter Login / X 登录

```bash
# Open Chrome with remote debugging / 打开 Chrome 远程调试
open -a 'Google Chrome' --args --remote-debugging-port=9222
# Log in to X/Twitter in that Chrome window, then run:
# 在弹出的 Chrome 中登录 X，然后运行：
python login_save_session.py
```

### Step 4 — Customize (optional) / 个性化（可选）

| File / 文件 | What to edit / 改什么 |
|---|---|
| `config/user_profile.md` | Your interests & Key Players / 你的兴趣和关键实体 |
| `config/sources.yaml` | Enable/disable/add sources / 开关或添加信息源 |
| `config/preferences.md` | Memo format & filtering rules / 简报格式和筛选规则 |

### Step 5 — Test / 验证

```bash
python -m src.pipeline
# "Pipeline completed" = success ✓
```

### Step 6 — Schedule / 定时运行

**Scraping / 爬取** — add to crontab:
```
0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1
```

**Memo generation / 简报生成** — create an OpenClaw cron job ~20 min after scraping. It reads `feed_slim.json` + `config/` files, generates the brief, and sends it to you.

---

## Adding Sources / 添加源

4 lines in `config/sources.yaml`, zero code:

```yaml
- name: my-favorite-blog
  type: rss
  enabled: true
  url: https://example.com/feed.xml
  tags: [blog]
```

The starter list includes: X/Twitter, Hacker News, GitHub Trending, AI company blogs, tech media, indie blogs, VC blogs, arXiv, Reddit, Product Hunt, Tavily search. See `config/sources.yaml` for the full list.

---

## X-Push (Optional) / X-Push（可选）

Real-time X/Twitter highlights every 2 hours, complementing the daily brief.

每 2 小时推送 X/Twitter 上的新鲜事，与每日简报互补。

Set up an OpenClaw cron job running `push/run.sh` every 2 hours. Customize `push/user_profile.md`.

---

## Architecture / 架构

See [docs/architecture.md](docs/architecture.md) for the full diagram.

```
Scrape (crontab)                      Memo (OpenClaw cron)
────────────────                      ────────────────────
python -m src.pipeline                LLM reads feed_slim.json
  ├─ Fetch all enabled sources          ├─ Reads config/*
  ├─ Dedup (URL + title + cross-day)    ├─ Generates 5-section brief
  └─ Write feed_slim.json               └─ Sends to user + saves memo
```

**Key decisions / 设计决策:**
- Config-driven: add RSS source = 4 lines YAML / 加 RSS 源 = 4 行 YAML
- Memo-based cross-day dedup / 跨天去重基于 memo
- Two-phase cron: scrape and memo run separately / 爬取和生成分开
- 7-day freshness filter on RSS / RSS 7 天时效过滤

---

## License

MIT
