# Multi-Source Feed 📡

AI-curated daily tech brief from customizable sources, delivered via your preferred messaging channel.

AI 驱动的每日科技简报，聚合多个可配置信息源，通过你配置的消息通道推送。

---

## How It Works / 工作原理

```
Your Sources                  Pipeline                     You
┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐
│ X/Twitter        │    │                  │    │              │
│ Hacker News      │    │  Fetch → Dedup   │    │  Daily Brief │
│ GitHub Trending  │───▶│  → Filter        │───▶│  (~25 items) │
│ AI Blogs (RSS)   │    │  → LLM Memo      │    │              │
│ Tech Media (RSS) │    │                  │    │  Structured  │
│ Indie Blogs      │    └──────────────────┘    │  5 sections  │
│ Reddit           │     09:00 scrape            └──────────────┘
│ Product Hunt     │     09:20 memo generate
│ Web Search       │
│ + your own RSS   │
└──────────────────┘
```

**Included source types / 支持的源类型：**
X/Twitter, Hacker News, GitHub Trending, AI company blogs (RSS), tech media (RSS), independent blogs, VC blogs, arXiv, Reddit, Product Hunt, Tavily web search. See `config/sources.yaml` for the full starter list — add, remove, or swap sources freely.

**Memo Sections / 简报板块:**
🧠 Tech & Models · 🚀 Products & Tools · 💡 Ideas · ♟️ Business & Strategy · 🔭 Signals

---

## Quick Start / 快速开始

### Prerequisites / 前提条件

- Python 3.9+
- [OpenClaw](https://openclaw.ai) (for memo generation & delivery)
- A messaging channel configured in OpenClaw (Telegram, Discord, Feishu, etc.)

### Option A: Install via ClawHub / 通过 ClawHub 安装

```bash
npx clawhub install multi-source-feed
```

Then ask your OpenClaw agent: **"help me set up multi-source-feed"** — it will guide you through everything interactively.

然后对 OpenClaw agent 说：**"帮我设置 multi-source-feed"** — 它会交互式引导你完成所有步骤。

### Option B: Manual Setup / 手动安装

```bash
# 1. Clone / 克隆
git clone https://github.com/Jadeenn/multi-source-feed.git
cd multi-source-feed

# 2. Install dependencies / 安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Configure API keys / 配置 API 密钥
cp .env.example .env
# Edit .env — fill in your TAVILY_API_KEY and PRODUCTHUNT_API_TOKEN
# 编辑 .env — 填入你的 TAVILY_API_KEY 和 PRODUCTHUNT_API_TOKEN

# 4. X/Twitter login / X 登录
python login_save_session.py
# A browser will open — log in to your X account, then close the browser.
# 浏览器会弹出 — 登录你的 X 账号，然后关闭浏览器。

# 5. Test run / 验证
python -m src.pipeline
# You should see "Pipeline completed" with items from all enabled sources.
# 你应该看到 "Pipeline completed"，包含所有已启用源的数据。
```

### Schedule / 设置定时

**Scraping (crontab) / 爬取：**
```bash
# Run daily at 09:00 / 每天 09:00 运行
crontab -e
# Add: 0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1
```

**Memo generation (OpenClaw cron) / 简报生成：**

Create an OpenClaw cron job that runs ~20 minutes after scraping. The job should:

创建一个 OpenClaw cron job，在爬取后约 20 分钟运行：

1. Read `config/user_profile.md` and `config/preferences.md`
2. Read `feed_slim.json` (the pipeline output)
3. Generate a daily brief following the preferences format
4. Send the brief to the user
5. Save the brief to `memo/YYYY-MM-DD.md`

---

## Customization / 自定义配置

All customizable files are in `config/`. You only need to touch this directory.

所有可自定义文件都在 `config/` 目录下。你只需要修改这个目录。

| File / 文件 | Purpose / 用途 |
|---|---|
| `config/user_profile.md` | Your interests & Key Players to track / 你的兴趣和需要追踪的关键实体 |
| `config/sources.yaml` | Enable/disable/add sources / 开关或添加信息源 |
| `config/preferences.md` | Memo format, sections, filtering rules / 简报格式、板块、筛选规则 |

### Adding a new RSS source / 添加 RSS 源

Just 4 lines in `config/sources.yaml` — zero code:

```yaml
- name: my-favorite-blog
  type: rss
  enabled: true
  url: https://example.com/feed.xml
  tags: [blog]
```

### Changing your interests / 修改兴趣方向

Edit `config/user_profile.md`. The LLM uses this to filter and prioritize items.

修改 `config/user_profile.md`，LLM 会根据这个文件来筛选和排序内容。

---

## X-Push (Optional) / X-Push（可选）

X-Push sends real-time X/Twitter highlights every 2 hours — complementing the daily brief with breaking updates.

X-Push 每 2 小时推送 X/Twitter 上的新鲜事——与每日简报互补，捕捉实时动态。

To enable, set up an OpenClaw cron job running `push/run.sh` every 2 hours. Customize `push/user_profile.md` with your interests.

启用方法：设置一个 OpenClaw cron job 每 2 小时运行 `push/run.sh`。在 `push/user_profile.md` 中自定义你的兴趣。

---

## Architecture / 架构

See [docs/architecture.md](docs/architecture.md) for the full system diagram.

```
Scrape (crontab, pure Python)          Memo (OpenClaw cron, LLM)
─────────────────────────────          ──────────────────────────
09:00  python -m src.pipeline          09:20  LLM reads feed_slim.json
  │                                      │
  ├─ Fetch all enabled sources            ├─ Reads config/user_profile.md
  ├─ Intra-day dedup (URL + title)       ├─ Reads config/preferences.md
  ├─ Cross-day dedup (memo/*.md)         ├─ Generates 5-section brief
  ├─ Write feed_merged.json              ├─ Sends to user
  └─ Write feed_slim.json (LLM input)   └─ Saves memo/YYYY-MM-DD.md
```

**Key design decisions / 关键设计决策:**
- **Config-driven sources**: Adding an RSS source = 4 lines of YAML, zero code / 配置驱动：加 RSS 源 = 4 行 YAML
- **Memo-based cross-day dedup**: Compares against delivered memos, not raw data / 跨天去重基于已推送的 memo
- **Two-phase cron**: Scraping (pure Python) and memo (LLM) run separately / 双阶段 cron：爬取和生成分开运行
- **7-day freshness filter**: RSS and blog sources auto-filter items older than 7 days / 7 天时效过滤

---

## Tech Stack / 技术栈

- **Language**: Python 3.9+
- **X scraper**: Playwright (headed Chrome, cookie-based auth)
- **HTTP**: requests + BeautifulSoup
- **RSS**: feedparser
- **APIs**: Algolia (HN), GraphQL (Product Hunt), JSON (Reddit), Tavily (web search)
- **Scheduling**: crontab (scrape) + OpenClaw cron (memo)
- **LLM**: Any model supported by OpenClaw

---

## License

MIT
