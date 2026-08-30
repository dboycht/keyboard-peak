"""从浏览器读取 3D 渲染的真实柱子尺寸（开发验证用）。"""
import asyncio
import json
import sys

from playwright.async_api import async_playwright


async def main(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1680, "height": 1000})
        await page.goto(url, wait_until="load", timeout=20000)
        await page.wait_for_timeout(5000)

        await page.click('.mode-btn[data-mode="cover"]')
        await page.wait_for_timeout(4000)

        debug = await page.evaluate("() => window.__kpeakDebug ? JSON.stringify(window.__kpeakDebug()) : 'no-debug'")
        print("cover mode:", debug)

        await page.click('.mode-btn[data-mode="classic"]')
        await page.wait_for_timeout(4000)
        debug2 = await page.evaluate("() => window.__kpeakDebug ? JSON.stringify(window.__kpeakDebug()) : 'no-debug'")
        print("classic mode:", debug2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))