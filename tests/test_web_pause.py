"""网页端「暂停旋转」按钮交互验证 + 截图。"""
import asyncio
import json
import os
import subprocess
import sys
import time

from playwright.async_api import async_playwright


async def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)
    port = "8915"
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

            # 初始：自动旋转开启
            dbg = json.loads(await page.evaluate("() => JSON.stringify(window.__kpeakDebug())"))
            print("初始 autoRotate:", dbg["autoRotate"], flush=True)
            assert dbg["autoRotate"] is True

            # 初始按钮文本
            t0 = await page.text_content("#pauseText")
            print("初始按钮:", t0, flush=True)
            assert t0 == "暂停旋转", t0

            # 点击 → 暂停旋转
            await page.click("#pauseBtn")
            await page.wait_for_timeout(800)
            t1 = await page.text_content("#pauseText")
            print("点击后按钮:", t1, flush=True)
            assert t1 == "恢复旋转", t1
            dbg1 = json.loads(await page.evaluate("() => JSON.stringify(window.__kpeakDebug())"))
            print("点击后 autoRotate:", dbg1["autoRotate"], flush=True)
            assert dbg1["autoRotate"] is False
            await page.screenshot(path="docs/v104_rot_paused.png")

            # 再次点击 → 恢复旋转
            await page.click("#pauseBtn")
            await page.wait_for_timeout(800)
            t2 = await page.text_content("#pauseText")
            assert t2 == "暂停旋转", t2
            dbg2 = json.loads(await page.evaluate("() => JSON.stringify(window.__kpeakDebug())"))
            assert dbg2["autoRotate"] is True
            print("恢复后 autoRotate:", dbg2["autoRotate"], flush=True)

            print("pageerror:", len(errors), flush=True)
            assert not errors, errors
            await browser.close()
        print("=== 网页暂停旋转按钮 PASS ===", flush=True)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            proc.kill()


asyncio.run(main())