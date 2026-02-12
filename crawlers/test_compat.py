#!/usr/bin/env python3
"""Quick test to find compatibility pagination mechanism."""
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time

JS_FIND_CONTROLS = """() => {
    const info = {};
    const wrapper = document.getElementById("d-motors-compatibility-table");
    if (!wrapper) { info.no_wrapper = true; return info; }

    const els = wrapper.querySelectorAll("button, a, [role=button], nav");
    info.controls = [];
    els.forEach(b => {
        info.controls.push({
            tag: b.tagName,
            text: b.textContent.trim().substring(0, 80),
            cls: (b.className || "").substring(0, 120),
            testid: b.getAttribute("data-testid") || "",
        });
    });

    const text = wrapper.innerText;
    info.tail = text.substring(Math.max(0, text.length - 800));

    return info;
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}, locale="en-GB",
    )
    Stealth().apply_stealth_sync(context)
    page = context.new_page()

    page.goto("https://www.ebay.co.uk", wait_until="load", timeout=30000)
    time.sleep(3)
    try:
        btn = page.locator("#gdpr-banner-accept")
        if btn.is_visible(timeout=3000):
            btn.click()
            time.sleep(2)
    except:
        pass

    page.goto("https://www.ebay.co.uk/itm/133937033683", wait_until="load", timeout=30000)
    time.sleep(6)

    result = page.evaluate(JS_FIND_CONTROLS)
    for k, v in result.items():
        print(f"{k}: {v}", flush=True)

    browser.close()
