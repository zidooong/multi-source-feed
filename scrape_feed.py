import json
import re
import time
import signal
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

# ============================================================
#  配置
# ============================================================
TARGET_POSTS_PER_TAB = 60   # 每个 tab 抓取目标条数（合并去重后总数会少一些）
MAX_SCROLLS = 70            # 每个 tab 最多滚动次数
WAIT_SECONDS = 3            # 每次滚动后等待秒数
SCRAPE_TRENDING = True      # 是否爬取 Explore/Trending 页
TRENDING_TOPIC_COUNT = 10   # 抓取多少个 trending 话题

# 健壮性配置
MAX_RETRIES = 3             # 页面加载重试次数
RETRY_DELAY = 5             # 重试间隔秒数
STALE_SCROLL_LIMIT = 5      # 连续多少次滚动无新帖则提前退出
GLOBAL_TIMEOUT = 600         # 全局超时秒数（10分钟）


# ============================================================
#  全局超时保护
# ============================================================
def timeout_handler(signum, frame):
    print("\n❌ 全局超时！正在保存已有数据并退出...")
    raise TimeoutError("Global timeout reached")

# 仅在支持 SIGALRM 的系统上设置（Linux/macOS）
if hasattr(signal, 'SIGALRM'):
    signal.signal(signal.SIGALRM, timeout_handler)


# ============================================================
#  重试工具
# ============================================================
def retry(func, *args, retries=MAX_RETRIES, delay=RETRY_DELAY, desc="操作"):
    """通用重试包装器"""
    for attempt in range(1, retries + 1):
        try:
            return func(*args)
        except Exception as e:
            print(f"   ⚠️ {desc} 第 {attempt} 次失败: {e}")
            if attempt < retries:
                print(f"   ⏳ {delay}s 后重试...")
                time.sleep(delay)
            else:
                print(f"   ❌ {desc} 已达最大重试次数 ({retries})")
                raise

# ============================================================
#  主流程
# ============================================================
def scrape_feed():
    # 启动全局超时
    if hasattr(signal, 'SIGALRM'):
        signal.alarm(GLOBAL_TIMEOUT)

    # 用于存放部分结果，确保崩溃时也能保存
    partial_result = {
        "scraped_at": datetime.now().isoformat(),
        "stats": {},
        "trending": [],
        "posts": [],
    }

    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                storage_state="x_session.json",
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            # ---------- 1. 打开首页（带重试）----------
            print("🌐 打开 X 首页...")
            retry(
                lambda: page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000),
                retries=MAX_RETRIES, delay=RETRY_DELAY, desc="打开首页"
            )
            time.sleep(6)

            # ---------- 2. 先爬 For You（默认 tab）----------
            print("\n📌 ===== 开始爬取 For You tab =====")
            wait_for_tweets(page)
            for_you_posts = collect_posts(page, source="for_you")
            print(f"✅ For You 爬取完成: {len(for_you_posts)} 条")

            # 立即暂存，防止后续崩溃丢数据
            partial_result["posts"] = for_you_posts
            save_partial(partial_result, "feed_raw_partial.json")

            # ---------- 3. 切到 Following tab 爬取 ----------
            print("\n📌 ===== 切换到 Following tab =====")
            following_posts = []
            try:
                tab = page.locator('[role="tab"]:has-text("Following")')
                tab.first.click()
                time.sleep(4)

                # 强制回到页面顶部，避免从中间开始爬
                page.evaluate("window.scrollTo(0, 0)")
                time.sleep(2)

                # 验证是否真的切换成功：检查 tab 的 aria-selected
                try:
                    is_selected = tab.first.get_attribute("aria-selected")
                    if is_selected == "true":
                        print("   ✅ 已确认切换到 Following")
                    else:
                        print("   ⚠️ tab 点击了但 aria-selected 不是 true，可能没切换成功")
                except Exception:
                    pass

                wait_for_tweets(page)
                following_posts = collect_posts(page, source="following")
                print(f"✅ Following 爬取完成: {len(following_posts)} 条")
            except Exception as e:
                print(f"   ❌ Following 爬取失败: {e}，继续使用 For You 数据")

            # ---------- 4. 合并去重 ----------
            merged = merge_posts(for_you_posts, following_posts)
            print(f"\n📊 合并去重后总计: {len(merged)} 条")
            partial_result["posts"] = merged
            save_partial(partial_result, "feed_raw_partial.json")

            # ---------- 5. 爬取 Trending（可选）----------
            trending = []
            if SCRAPE_TRENDING:
                print("\n📌 ===== 开始爬取 Trending =====")
                try:
                    trending = scrape_trending(page)
                    print(f"✅ Trending 爬取完成: {len(trending)} 条")
                except Exception as e:
                    print(f"   ❌ Trending 爬取失败: {e}，跳过")

            # ---------- 6. 输出 ----------
            output = {
                "scraped_at": datetime.now().isoformat(),
                "stats": {
                    "for_you_raw": len(for_you_posts),
                    "following_raw": len(following_posts),
                    "merged_total": len(merged),
                    "trending_topics": len(trending),
                },
                "trending": trending,
                "posts": merged,
            }

            with open("feed_raw.json", "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print("\n💾 已保存到 feed_raw.json")

            browser.close()

            # 取消全局超时
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)

            return output

    except TimeoutError:
        print("⏰ 全局超时触发，保存已有数据...")
        save_partial(partial_result, "feed_raw.json")
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        return partial_result

    except Exception as e:
        print(f"\n❌ 意外错误: {e}")
        print("💾 尝试保存已有数据...")
        save_partial(partial_result, "feed_raw.json")
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        raise


def save_partial(data, filename):
    """保存部分结果到文件"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   💾 部分结果已暂存到 {filename}")
    except Exception as e:
        print(f"   ⚠️ 暂存失败: {e}")


# ============================================================
#  帖子收集（通用，支持两个 tab）
# ============================================================
def collect_posts(page, source="unknown"):
    """在当前 tab 滚动收集帖子"""
    all_posts = []
    seen_urls = set()      # 用 URL 去重比纯文本更可靠
    seen_texts = set()     # 文本去重作为 fallback
    scroll_count = 0
    stale_count = 0        # 连续无新帖计数

    while len(all_posts) < TARGET_POSTS_PER_TAB and scroll_count < MAX_SCROLLS:
        scroll_count += 1
        prev_count = len(all_posts)
        print(f"   🔄 第 {scroll_count} 次滚动，已抓 {len(all_posts)}/{TARGET_POSTS_PER_TAB} 条...")

        articles = page.locator("article[data-testid='tweet']")
        count = articles.count()

        for j in range(count):
            try:
                article = articles.nth(j)
                post = extract_post(article)
                if post is None:
                    continue

                # 去重：优先用 URL，fallback 用文本
                dedup_key = post["url"] if post["url"] else post["text"]
                if dedup_key in seen_urls or post["text"] in seen_texts:
                    continue

                post["source"] = source  # 标记来源 tab
                seen_urls.add(dedup_key)
                seen_texts.add(post["text"])
                all_posts.append(post)

                if len(all_posts) >= TARGET_POSTS_PER_TAB:
                    break
            except Exception:
                continue

        if len(all_posts) >= TARGET_POSTS_PER_TAB:
            break

        # 防死循环：连续多次滚动无新帖则提前退出
        if len(all_posts) == prev_count:
            stale_count += 1
            if stale_count >= STALE_SCROLL_LIMIT:
                print(f"   ⚠️ 连续 {STALE_SCROLL_LIMIT} 次滚动无新帖，提前退出")
                break
        else:
            stale_count = 0

        page.evaluate("window.scrollBy(0, window.innerHeight * 3)")
        time.sleep(WAIT_SECONDS)

    return all_posts


# ============================================================
#  合并两个 tab 的帖子，去重并标记双来源
# ============================================================
def merge_posts(for_you_posts, following_posts):
    """合并两个 tab 的帖子，重复帖标记 source 为 both"""
    merged = {}

    for post in for_you_posts:
        key = post["url"] if post["url"] else post["text"]
        merged[key] = post

    for post in following_posts:
        key = post["url"] if post["url"] else post["text"]
        if key in merged:
            # 同一帖子在两个 tab 都出现，标记为 both
            merged[key]["source"] = "both"
            # 取较高的 views（有时两次抓取数字略有差异）
            merged[key]["views"] = max(merged[key]["views"], post["views"])
        else:
            merged[key] = post

    # 按 views 降序排列
    result = sorted(merged.values(), key=lambda x: x.get("views", 0), reverse=True)
    return result


# ============================================================
#  Trending 爬取
# ============================================================
def scrape_trending(page):
    """访问 Explore 页面，爬取 Trending 话题"""
    trending = []
    try:
        page.goto("https://x.com/explore/tabs/trending", wait_until="domcontentloaded", timeout=20000)
        time.sleep(5)

        # Trending 条目通常在 [data-testid="trend"] 或 cellInnerDiv 里
        trends = page.locator('[data-testid="trend"]')
        count = min(trends.count(), TRENDING_TOPIC_COUNT)

        for i in range(count):
            try:
                trend = trends.nth(i)
                entry = {}

                # 话题名称：通常是 trend 里最显眼的文本
                texts = trend.locator("span").all()
                text_contents = []
                for t in texts:
                    try:
                        txt = t.inner_text(timeout=1000).strip()
                        if txt:
                            text_contents.append(txt)
                    except Exception:
                        continue

                # 尝试提取话题名（通常是最长或最突出的 span）
                entry["topic"] = ""
                entry["category"] = ""
                entry["post_count"] = ""

                for txt in text_contents:
                    txt_lower = txt.lower()
                    # 类别行通常包含 "· Trending" 或具体类别
                    if "trending" in txt_lower or "·" in txt:
                        entry["category"] = txt
                    # 帖子数：包含 "posts"/"tweets"，或独立的数字格式（如 "21K", "1,234"）
                    elif ("post" in txt_lower or "tweet" in txt_lower
                          or _looks_like_count(txt)):
                        entry["post_count"] = txt
                    # 其余最长的文本作为话题名
                    elif len(txt) > len(entry["topic"]):
                        entry["topic"] = txt

                if entry["topic"]:
                    trending.append(entry)
            except Exception:
                continue

    except Exception as e:
        print(f"   ⚠️ Trending 爬取失败: {e}")

    return trending


# ============================================================
#  单条帖子提取
# ============================================================
def extract_post(article):
    post = {}

    # --- 检测是否为广告 ---
    try:
        ad_indicators = article.locator('span:has-text("Ad")').all()
        for indicator in ad_indicators:
            txt = indicator.inner_text(timeout=500).strip()
            if txt == "Ad":
                return None  # 直接跳过广告
    except Exception:
        pass

    # --- 检测是否为转推 (Retweet) ---
    post["is_retweet"] = False
    post["retweeted_by"] = ""
    try:
        # 转推会在帖子上方显示 "XXX reposted" 的社交信息
        social_context = article.locator('[data-testid="socialContext"]')
        if social_context.count() > 0:
            context_text = social_context.inner_text(timeout=2000)
            if "reposted" in context_text.lower():
                post["is_retweet"] = True
                post["retweeted_by"] = context_text.replace(" reposted", "").strip()
    except Exception:
        pass

    # --- 作者 handle ---
    try:
        for link in article.locator('a[role="link"]').all():
            href = link.get_attribute("href") or ""
            if href.startswith("/") and href.count("/") == 1 and href != "/":
                post["author_handle"] = href.strip("/")
                break
    except Exception:
        post["author_handle"] = ""

    # --- 作者显示名 ---
    try:
        post["author_name"] = article.locator('a[role="link"] span').first.inner_text(timeout=2000)
    except Exception:
        post["author_name"] = ""

    # --- 帖子正文 ---
    try:
        text_el = article.locator("div[data-testid='tweetText']")
        post["text"] = text_el.inner_text(timeout=2000) if text_el.count() > 0 else ""
    except Exception:
        post["text"] = ""

    if not post["text"]:
        return None

    # --- 帖子 URL 和时间戳 ---
    try:
        time_el = article.locator("time")
        href = time_el.locator("..").first.get_attribute("href") or ""
        post["url"] = f"https://x.com{href}" if href else ""
    except Exception:
        post["url"] = ""

    try:
        post["timestamp"] = article.locator("time").get_attribute("datetime") or ""
    except Exception:
        post["timestamp"] = ""

    # --- 互动指标 ---
    try:
        buttons = article.locator('[role="group"] button').all()
        labels = []
        for btn in buttons:
            try:
                labels.append(btn.get_attribute("aria-label") or "")
            except Exception:
                continue
        post.update(parse_metrics(labels))
    except Exception:
        post.update({"replies": 0, "reposts": 0, "likes": 0, "bookmarks": 0})

    # --- Views（多策略提取）---
    post["views"] = extract_views(article)

    # --- 外部链接 ---
    try:
        seen_hrefs = set()
        links = []
        for a in article.locator("a[href]").all():
            href = a.get_attribute("href") or ""
            if (href.startswith("http")
                    and "x.com" not in href
                    and "twitter.com" not in href
                    and "t.co" not in href      # t.co 短链接通常会展开，单独排除
                    and href not in seen_hrefs):
                link_text = ""
                try:
                    link_text = a.inner_text(timeout=1000).strip()
                except Exception:
                    pass
                links.append({
                    "url": href,
                    "text": link_text if link_text else ""
                })
                seen_hrefs.add(href)
        post["external_links"] = links
    except Exception:
        post["external_links"] = []

    # --- 引用推文 ---
    try:
        quoted = article.locator('[data-testid="tweet"] [data-testid="tweet"]')
        if quoted.count() > 0:
            q = quoted.first.locator("div[data-testid='tweetText']")
            post["quoted_tweet"] = q.inner_text(timeout=2000) if q.count() > 0 else ""
        else:
            post["quoted_tweet"] = ""
    except Exception:
        post["quoted_tweet"] = ""

    # --- 是否包含媒体 ---
    post["has_media"] = False
    try:
        media_selectors = [
            '[data-testid="tweetPhoto"]',
            '[data-testid="videoPlayer"]',
            '[data-testid="card.wrapper"]',
        ]
        for sel in media_selectors:
            if article.locator(sel).count() > 0:
                post["has_media"] = True
                break
    except Exception:
        pass

    return post


# ============================================================
#  Views 提取（多策略）
# ============================================================
def extract_views(article):
    """多策略提取 views 数"""

    # 策略1: aria-label 里包含 "view"
    try:
        view_candidates = article.locator('a[href*="/analytics"]').all()
        for el in view_candidates:
            label = el.get_attribute("aria-label") or ""
            if "view" in label.lower():
                num = parse_number_from_text(label)
                if num > 0:
                    return num
    except Exception:
        pass

    # 策略2: app-text-transition-container（views 计数器）
    try:
        # views 通常是 group 区域最后一个数字
        group = article.locator('[role="group"]')
        if group.count() > 0:
            containers = group.locator('[data-testid="app-text-transition-container"]').all()
            if containers:
                # 最后一个通常是 views
                last = containers[-1]
                txt = last.inner_text(timeout=1000).strip()
                num = parse_abbreviated_number(txt)
                if num > 0:
                    return num
    except Exception:
        pass

    # 策略3: 直接找 analytics 链接的文本
    try:
        analytics_links = article.locator('a[href*="/analytics"]').all()
        for link in analytics_links:
            txt = link.inner_text(timeout=1000).strip()
            if txt:
                num = parse_abbreviated_number(txt)
                if num > 0:
                    return num
    except Exception:
        pass

    return 0


# ============================================================
#  数字解析工具
# ============================================================
def _looks_like_count(text):
    """判断文本是否像帖子计数，如 '21K', '1,234', '50.2K'"""
    return bool(re.match(r'^[\d,.]+[KkMm]?(\+)?\s*(posts?|tweets?)?$', text.strip()))


def parse_number_from_text(text):
    """从文本中提取纯数字"""
    num = "".join(c for c in text.replace(",", "") if c.isdigit())
    return int(num) if num else 0


def parse_abbreviated_number(text):
    """解析缩写数字，如 1.4M, 102K, 93.5K"""
    text = text.strip().replace(",", "")
    try:
        if "M" in text.upper():
            return int(float(text.upper().replace("M", "")) * 1_000_000)
        elif "K" in text.upper():
            return int(float(text.upper().replace("K", "")) * 1_000)
        else:
            num = "".join(c for c in text if c.isdigit())
            return int(num) if num else 0
    except ValueError:
        return 0


# ============================================================
#  互动指标解析
# ============================================================
def parse_metrics(labels):
    result = {"replies": 0, "reposts": 0, "likes": 0, "bookmarks": 0}
    for label in labels:
        label_lower = label.lower()
        for key in result:
            if key.rstrip("s") in label_lower or key in label_lower:
                num = parse_number_from_text(label)
                if num:
                    result[key] = num
    return result


# ============================================================
#  等待推文加载
# ============================================================
def wait_for_tweets(page):
    """等待推文加载完成"""
    print("   ⏳ 等待帖子加载...")
    try:
        page.wait_for_selector("article[data-testid='tweet']", timeout=15000)
        time.sleep(2)
    except Exception:
        print("   ⚠️ 等待超时，继续尝试")


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    scrape_feed()