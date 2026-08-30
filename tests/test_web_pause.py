"""网页端暂停按钮交互验证 + 截图。"""
import asyncio
import os
import subprocess
import sys
import time

from playwright.async_api import async_playwright


async def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    port = "8914"
    proc = subprocess.Popen(
        [sys.executable, "start.py", "--demo", "--no-browser", "--port", port],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(4)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1680, "height": 1000})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            await page.goto(f"http://127.0.0.1:{port}", wait_until="load", timeout=20000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path="docs/v104.png")
            print("saved v104.png", flush=True)

            # 初始按钮文本应为「暂停采集」
            t0 = await page.text_content("#pauseText")
            print("初始按钮:", t0, flush=True)
            assert t0 == "暂停采集", t0

            # 点击 → 暂停
            await page.click("#pauseBtn")
            await page.wait_for_timeout(1500)
            t1 = await page.text_content("#pauseText")
            print("点击后按钮:", t1, flush=True)
            assert t1 == "恢复采集", t1
            # 截图保持暂停状态
            await page.screenshot(path="docs/v104_paused.png")
            print("saved v104_paused.png", flush=True)

            # 再次点击 → 恢复
            await page.click("#pauseBtn")
            await page.wait_for_timeout(1200)
            t2 = await page.text_content("#pauseText")
            print("再点后按钮:", t2, flush=True)
            assert t2 == "暂停采集", t2

            print("pageerror:", len(errors), flush=True)
            for e in errors[:5]:
                print("  ", str(e)[:200], flush=True)
            assert not errors, "页面有报错"
            await browser.close()
        print("=== 网页暂停按钮 PASS ===", flush=True)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            proc.kill()


asyncio.run(main())