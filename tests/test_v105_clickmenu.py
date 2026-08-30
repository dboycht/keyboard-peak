"""调试点击菜单：抓 console 错误 + 直接测菜单核心逻辑。"""
import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright


async def main():
    url = "http://127.0.0.1:8924"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1680, "height": 1000})
        console_msgs = []
        page.on("console", lambda m: console_msgs.append(f"[{m.type}] {m.text[:200]}"))
        page.on("pageerror", lambda e: console_msgs.append(f"[pageerror] {str(e)[:300]}"))
        await page.goto(url, wait_until="load", timeout=20000)
        await page.wait_for_timeout(4000)

        # 检查 main.js 是否正常加载（暂停按钮应在）
        has_pause = await page.evaluate("() => !!document.getElementById('pauseBtn')")
        print("pauseBtn 存在:", has_pause, flush=True)

        # 直接试点击暂停旋转按钮（已知 UI 元素可点击，验证 JS 事件系统没问题）
        await page.click("#pauseBtn")
        await page.wait_for_timeout(300)
        pause_text = await page.text_content("#pauseText")
        print("点击暂停按钮后文本:", pause_text, flush=True)

        # 用调试钩子验证菜单显示逻辑（模拟 showKeyMenu 调用）
        menu_test = await page.evaluate("""
            () => {
                window.__kpeakDebug().testMenu('SPACE', 300, 300);
                const d = document.getElementById('keyMenu').style.display;
                const label = document.getElementById('menuKeyLabel').textContent;
                const stat = document.getElementById('menuStat').textContent;
                return d + '|' + label + '|' + stat;
            }
        """)
        print("菜单测试:", menu_test, flush=True)
        assert menu_test.startswith("block"), "菜单未显示"
        assert "SPACE" in menu_test or "␣" in menu_test, "菜单标题错误"

        # 点击「隐藏该键柱体」
        await page.click("#menuHide")
        await page.wait_for_timeout(300)
        hidden_display = await page.evaluate("() => document.getElementById('keyMenu').style.display")
        print("点击隐藏后菜单 display:", hidden_display, flush=True)
        assert hidden_display == "none", "菜单未关闭"

        # 点击「恢复所有隐藏柱体」（先重新打开菜单）
        await page.evaluate("() => window.__kpeakDebug().testMenu('E', 300, 300)")
        await page.wait_for_timeout(200)
        await page.click("#menuUnhide")
        await page.wait_for_timeout(200)

        await page.screenshot(path="docs/v105_menu.png")
        print("console 消息:")
        for m in console_msgs[:15]:
            print("  ", m, flush=True)
        await browser.close()
        print("=== 点击菜单功能 PASS ===", flush=True)


asyncio.run(main())