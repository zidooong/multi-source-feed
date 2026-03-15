---
name: multi-source-feed
description: Set up and manage an AI-curated daily tech brief from customizable sources. Use when user says "set up multi-source-feed", "configure my daily brief", or "msf setup".
version: 1.0.0
metadata: {"openclaw":{"emoji":"📡","requires":{"bins":["python3"],"env":["TAVILY_API_KEY"]},"primaryEnv":"TAVILY_API_KEY","homepage":"https://github.com/Jadeenn/multi-source-feed"}}
---

# Multi-Source Feed

AI-curated daily tech brief aggregated from customizable sources (X, HN, GitHub Trending, RSS blogs, Reddit, Product Hunt, Tavily, and more). Deduplicates, filters by your interests, and delivers a structured memo.

## Setup

When the user asks to set up Multi-Source Feed, follow these steps **in order**. Execute each step automatically. If any step fails, print the manual command and continue.

### Step 1: Clone & Install

```bash
cd ~ && git clone https://github.com/Jadeenn/multi-source-feed.git
cd ~/multi-source-feed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

If clone already exists, skip to `pip install`.

### Step 2: API Keys

Ask the user for two API keys:

1. **Tavily** (free): sign up at https://tavily.com and copy the API key
2. **Product Hunt** (free): get a developer token at https://api.producthunt.com/v2/docs

Once the user provides both keys, write them to `~/multi-source-feed/.env`:

```
TAVILY_API_KEY=<user's key>
PRODUCTHUNT_API_TOKEN=<user's key>
```

### Step 3: X/Twitter Login

Tell the user:
> "To save your X/Twitter session, you need to:
> 1. Open Chrome with remote debugging enabled by running:
>    `open -a 'Google Chrome' --args --remote-debugging-port=9222`
> 2. Log in to X/Twitter in that Chrome window
> 3. Once logged in, I'll run a script that connects to that browser and saves your session cookies."

After the user confirms they are logged in to X in Chrome, run:

```bash
cd ~/multi-source-feed && source .venv/bin/activate && python login_save_session.py
```

This script connects to the already-open Chrome instance via CDP (Chrome DevTools Protocol) on port 9222, extracts the session/cookies, and saves them to `x_session.json` in the project root. It does **not** open a new browser window — it requires Chrome to already be running with `--remote-debugging-port=9222`.

### Step 4: Personalize (Optional)

Ask the user:
> "The default profile is set up for AI/tech product enthusiasts. Would you like to customize your interests, or use the defaults?"

If they want to customize:
- Read `config/user_profile.md`, modify based on their described interests
- Optionally adjust `config/sources.yaml` (enable/disable sources)
- Optionally adjust `config/preferences.md` (change memo sections/style)

If they say "skip" or "defaults are fine", move on.

### Step 5: Test Run

```bash
cd ~/multi-source-feed && source .venv/bin/activate && python -m src.pipeline
```

Show the user the output summary (number of sources, items fetched, any errors). If successful, show 5-10 sample titles from `feed_slim.json`.

### Step 6: Schedule

**Scraping (crontab):**
```bash
(crontab -l 2>/dev/null; echo "0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1") | crontab -
```

**Memo generation (OpenClaw cron):**
Create an OpenClaw cron job that runs daily (e.g., 20 minutes after scrape). The job should:
1. Check if `feed_slim.json` exists and is from today
2. Read `config/user_profile.md` and `config/preferences.md`
3. Read `feed_slim.json`
4. Generate the daily brief following preferences.md format
5. Send the memo to the user via their configured channel
6. Save the memo to `memo/YYYY-MM-DD.md`

Tell the user:
> "Setup complete! Your daily brief will be generated every morning. You'll receive it through your configured messaging channel."

## Manual Setup Fallback

If automated setup fails, provide the user with these commands to run manually:

```bash
# 1. Clone
git clone https://github.com/Jadeenn/multi-source-feed.git && cd multi-source-feed

# 2. Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. X Login
python login_save_session.py

# 5. Test
python -m src.pipeline

# 6. Schedule scraping
crontab -e
# Add: 0 9 * * * cd ~/multi-source-feed && .venv/bin/python3 -m src.pipeline >> /tmp/msf-scrape.log 2>&1
```

## Customization

All user-customizable files are in `config/`:

| File | Purpose |
|------|---------|
| `config/user_profile.md` | Your interests, Key Players to track |
| `config/sources.yaml` | Enable/disable sources, add RSS feeds |
| `config/preferences.md` | Memo format, sections, filtering rules |

### Adding a new RSS source

Add 4 lines to `config/sources.yaml`:
```yaml
- name: my-blog
  type: rss
  enabled: true
  url: https://example.com/feed.xml
  tags: [blog]
```

## X-Push (Optional)

X-Push sends real-time X/Twitter highlights every 2 hours. To enable:

1. Set up an OpenClaw cron job running `push/run.sh` every 2 hours
2. Customize `push/user_profile.md` with your interests
3. The push module shares `x_session.json` and `.venv` with the main pipeline

## Architecture

Your configured sources → Python pipeline → dedup (URL + title similarity + cross-day memo) → `feed_slim.json` → LLM generates structured memo → delivered to user.

See `docs/architecture.md` for the full system diagram.
