"""验证帧率限制逻辑：设低上限（5）应显著降低实际 FPS。"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright


async def main():
    url = "http://127.0.0.1:8924"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(url, wait_until="load", timeout=20000)
        await page.wait_for_timeout(3500)

        async def get_fps():
            dbg = json.loads(await page.evaluate("() => JSON.stringify(window.__kpeakDebug())"))
            return dbg["fps"], dbg["frameLimit"]

        fps0, lim0 = await get_fps()
        print(f"初始: fps={fps0} limit={lim0}", flush=True)

        # 设上限 30 fps（dropdown 有 30 选项）
        await page.select_option("#fpsLimit", "30")
        await page.wait_for_timeout(2500)
        fps1, lim1 = await get_fps()
        print(f"limit=30: fps={fps1} limit={lim1}", flush=True)
        assert lim1 == 30, "帧率限制未生效"

        # 恢复不限
        await page.select_option("#fpsLimit", "0")
        await page.wait_for_timeout(2500)
        fps2, lim2 = await get_fps()
        print(f"limit=0: fps={fps2} limit={lim2}", flush=True)
        assert lim2 == 0
        await browser.close()
    print("=== 帧率限制 PASS ===", flush=True)


asyncio.run(main())