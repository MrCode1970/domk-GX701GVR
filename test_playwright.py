#!/usr/bin/env python3
"""
Smoke test для Playwright.
Открывает example.com, выводит title, сохраняет screenshot.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path

def main():
    screenshot_path = Path("audit/example.png")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        print(f"📖 Открываю https://example.com...")
        page.goto("https://example.com")
        
        title = page.title()
        print(f"✅ Title: {title}")
        
        print(f"📸 Сохраняю скриншот: {screenshot_path}")
        page.screenshot(path=str(screenshot_path))
        
        browser.close()
        print(f"✅ Done!")
        
        return {
            "title": title,
            "screenshot": str(screenshot_path.resolve()),
        }

if __name__ == "__main__":
    result = main()
    print(f"\n📊 Результат:\n{result}")
