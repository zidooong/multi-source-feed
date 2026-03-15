# Multi-Source Feed 📡

AI-curated daily tech brief from customizable sources, delivered via your preferred messaging channel.

```
Your Sources → Fetch → Dedup → LLM Memo → Daily Brief (5 sections)
```

[English](#setup) | [中文](#安装)

---

## Setup

> **Prerequisites:** Python 3.9+, [OpenClaw](https://openclaw.ai), a messaging channel (Telegram, Discord, Feishu, etc.)

### Option A: OpenClaw auto-setup

```bash
npx clawhub install multi-source-feed
```

Then tell your OpenClaw agent: **"help me set up multi-source-feed"** — it handles Steps 1-6 below automatically.

> **Note:** Auto-setup quality depends on the LLM model powering your OpenClaw agent. Weaker models may fail mid-setup. If that happens, fall back to Option B.

### Option B: Manual setup

#### Step 1 — Install

```bash
git clone https://github.com/zidooong/multi-source-feed.git && cd multi-source-feed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
```

#### Step 2 — API Keys

Some sources require API keys. Tavily powers web search (catching trending topics not covered by any feed), and Product Hunt requires an API token for its GraphQL endpoint. Both are free.

```bash
cp .env.example .env
# Fill in TAVILY_API_KEY (free: https://tavily.com)
# Fill in PRODUCTHUNT_API_TOKEN (free: https://api.producthunt.com/v2/docs)
```

#### Step 3 — X/Twitter Login

X/Twitter has no public API for feed reading. The pipeline uses Playwright to scrape your X timeline via a real browser session. You need to log in once so it can save your session cookies.

```bash
# 1. Open Chrome with remote debugging
open -a 'Google Chrome' --args --remote-debugging-port=9222
# 2. Log in to X/Twitter in that Chrome window
# 3. Once logged in, save the session:
python login_save_session.py
```

#### Step 4 — Customize

**This step directly affects the quality of your daily brief.** The default profile is a generic template — customize it to match your interests, otherwise the LLM won't know what to prioritize or filter out.

| File | What to edit |
|---|---|
| `config/user_profile.md` | **Start here.** Your interests, what you don't care about, Key Players to track |
| `config/sources.yaml` | Enable/disable sources, add your own RSS feeds |
| `config/preferences.md` | Memo format, section definitions, filtering rules |

#### Step 5 — Test

Run the pipeline once to verify everything works: all sources can be fetched, API keys are valid, and X session is active.

```bash
python -m src.pipeline
# "Pipeline completed" = all sources fetched, dedup done, feed_slim.json written ✓
```

#### Step 6 — Schedule

The system runs in two phases. Phase 1 (scraping) must finish before Phase 2 (memo generation) starts.

**Phase 1: Scrape (crontab)** — Pure Python. Fetches all sources, deduplicates, and writes `feed_slim.json`.

```bash
crontab -e
# Add (runs daily at 09:00):
0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1
```

**Phase 2: Memo (OpenClaw cron)** — LLM-powered. Reads `feed_slim.json` + your `config/` files, generates a structured daily brief, and sends it via your messaging channel. Schedule ~20 min after Phase 1.

Create an OpenClaw cron job that:
1. Reads `config/user_profile.md` and `config/preferences.md` to understand your preferences
2. Reads `feed_slim.json` (the scrape output) as input data
3. Generates a daily brief following the preferences format
4. Sends the brief to you via your messaging channel
5. Saves the brief to `memo/YYYY-MM-DD.md` (used for cross-day dedup)

---

## Adding Sources

The starter `config/sources.yaml` includes a demo set of sources (X, HN, GitHub Trending, AI blogs, tech media, indie blogs, VC blogs, arXiv, Reddit, Product Hunt, Tavily search). **This list is not meant to be complete** — customize it for your own interests.

Adding a new RSS source = 4 lines, zero code:

```yaml
- name: my-favorite-blog
  type: rss
  enabled: true
  url: https://example.com/feed.xml
  tags: [blog]
```

---

## X-Push (Optional)

Real-time X/Twitter highlights every 2 hours, complementing the daily brief with breaking updates.

To enable: set up an OpenClaw cron job running `push/run.sh` every 2 hours. Customize `push/user_profile.md` with your interests. The push module shares `x_session.json` and `.venv` with the main pipeline — no extra setup needed.

---

## 安装

> **前提条件：** Python 3.9+、[OpenClaw](https://openclaw.ai)、一个消息渠道（Telegram、Discord、飞书等）

### 方式 A：OpenClaw 自动安装

```bash
npx clawhub install multi-source-feed
```

然后告诉 OpenClaw：**"帮我设置 multi-source-feed"**，它会自动完成以下步骤 1-6。

> **注意：** 自动安装效果取决于你 OpenClaw 使用的模型能力。如果模型较弱导致安装失败，请改用方式 B 手动安装。

### 方式 B：手动安装

#### 步骤 1 — 安装

```bash
git clone https://github.com/zidooong/multi-source-feed.git && cd multi-source-feed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
```

#### 步骤 2 — 配置密钥

部分数据源需要 API 密钥，需要自己注册并填入.env。Tavily 用于搜索热点话题（补充 RSS 覆盖不到的内容），Product Hunt 的 GraphQL 接口需要开发者 token。

```bash
cp .env.example .env
# 填入 TAVILY_API_KEY（免费：https://tavily.com）
# 填入 PRODUCTHUNT_API_TOKEN（免费：https://api.producthunt.com/v2/docs）
```

#### 步骤 3 — X/Twitter 登录

X/Twitter 没有公开的 feed 读取 API。Pipeline 通过 Playwright 用真实浏览器会话抓取你的 X 时间线，需要登录一次自己的账号以保存 session cookies。

```bash
# 1. 打开 Chrome 远程调试
open -a 'Google Chrome' --args --remote-debugging-port=9222
# 2. 在弹出的 Chrome 中登录 X
# 3. 登录后保存 session：
python login_save_session.py
```

#### 步骤 4 — 个性化

**这一步直接影响你每天收到的简报质量。** 默认配置是通用模板，你必须根据自己的兴趣定制，否则 LLM 不知道该重点关注什么、过滤掉什么。

| 文件 | 改什么 |
|---|---|
| `config/user_profile.md` | **从这里开始。** 定义你的兴趣、不关心的领域、需要追踪的关键实体 |
| `config/sources.yaml` | 开关信息源，添加你自己的 RSS |
| `config/preferences.md` | 简报格式、板块定义、筛选规则 |

#### 步骤 5 — 验证

运行一次 pipeline，验证所有环节：各数据源能否正常抓取、API 密钥是否有效、X session 是否生效。

```bash
python -m src.pipeline
# 看到 "Pipeline completed" = 所有源抓取成功，去重完成，feed_slim.json 已生成 ✓
```

#### 步骤 6 — 定时运行

系统分两个阶段运行。阶段 1（爬取）必须在阶段 2（生成简报）之前完成。

**阶段 1：爬取（crontab）**— 纯 Python 任务，抓取所有源、去重、输出 `feed_slim.json`。

```bash
crontab -e
# 添加这行（每天 09:00 运行）：
0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1
```

**阶段 2：生成简报（OpenClaw cron）**— LLM 任务，读取 `feed_slim.json` 和 `config/` 配置，生成结构化日报，通过你配置的消息渠道推送。需要在阶段 1 之后约 20 分钟运行。

创建一个 OpenClaw cron job：
1. 读取 `config/user_profile.md` 和 `config/preferences.md` 了解你的偏好
2. 读取 `feed_slim.json`（爬取输出）作为输入数据
3. 按 preferences 格式生成日报
4. 通过你的消息渠道发送
5. 保存到 `memo/YYYY-MM-DD.md`（用于跨天去重）

---

## 添加源

默认的 `config/sources.yaml` 包含一组示例源（X、HN、GitHub Trending、AI 博客、科技媒体、独立博客、VC 博客、arXiv、Reddit、Product Hunt、Tavily 搜索）。**这个列表不是完整的**，你应该根据自己的需求增删。

加一个 RSS 源 = 4 行 YAML，无需写代码：

```yaml
- name: my-favorite-blog
  type: rss
  enabled: true
  url: https://example.com/feed.xml
  tags: [blog]
```

---

## X-Push（可选）

每 2 小时推送 X/Twitter 上的亮点，与每日简报互补，捕捉实时动态。

启用方法：设置一个 OpenClaw cron job 每 2 小时运行 `push/run.sh`。在 `push/user_profile.md` 中自定义你的兴趣。push 模块与主 pipeline 共享 `x_session.json` 和 `.venv`，无需额外配置。

---

## License

MIT
