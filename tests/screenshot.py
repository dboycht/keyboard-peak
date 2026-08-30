"""用 Playwright 打开可视化页面，截取渲染效果图（开发验证用）。"""
import asyncio
import sys

from playwright.async_api import async_playwright


async def main(url: str, out: str, wait_ms: int = 8000):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1680, "height": 1000})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(url, wait_until="load", timeout=20000)
        await page.wait_for_timeout(wait_ms)
        await page.screenshot(path=out, full_page=False)
        print(f"screenshot saved: {out}")
        if errors:
            print("console errors:")
            for e in errors[:12]:
                print("  ", e[:300])
        else:
            print("no console errors")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8000))