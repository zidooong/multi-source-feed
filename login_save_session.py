from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # 连接到你已经打开的 Chrome
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0]

    # 把登录态保存到文件
    context.storage_state(path="x_session.json")
    print("✅ 登录态已保存到 x_session.json")

    browser.close()