from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=100,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    page = context.new_page()
    Stealth().apply_stealth_sync(page)
    
    page.goto("https://www.transfermarkt.co.uk")
    
    # Wait until the page body is fully loaded
    page.wait_for_selector("body", timeout=30000)
    
    # Extra wait for any redirects after verification
    page.wait_for_timeout(5000)
    
    print("Title:", page.title())
    print("URL:", page.url)
    
    # Keep browser open for 15 seconds so you can see it
    page.wait_for_timeout(15000)
    
    browser.close()