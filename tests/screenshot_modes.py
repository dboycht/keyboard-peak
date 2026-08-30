"""用 Playwright 打开可视化页面，切换显示模式并截图（开发验证用）。

用法: python tests/screenshot_modes.py <url> <out_dir> [等待毫秒]
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright


async def main(url: str, out_dir: str, wait_ms: int = 6000):
    os.makedirs(out_dir, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1680, "height": 1000})
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(url, wait_until="load", timeout=20000)
        await page.wait_for_timeout(wait_ms)

        modes = [("classic", "经典柱"), ("cover", "覆盖柱"), ("heat", "热力图")]
        for key, label in modes:
            await page.click(f'.mode-btn[data-mode="{key}"]')
            await page.wait_for_timeout(2500)  # 等待柱体过渡动画
            shot = os.path.join(out_dir, f"mode_{key}.png")
            await page.screenshot(path=shot, full_page=False)
            print(f"saved: {shot}", flush=True)

        if errors:
            print("console errors:")
            for e in errors[:12]:
                print("  ", e[:300])
        else:
            print("no console errors")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 6000))