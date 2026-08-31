# -*- coding: utf-8 -*-
"""skill 共享模块：SELL_URL / CHROME / PROFILE / 登录（替代 publish_auto——自包含）"""
import os
import time

BASE = os.path.dirname(os.path.abspath(__file__))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(BASE, ".profile")
SELL_URL = "https://myseller.taobao.com/home.htm/SellManage/on_sale?current=1&pageSize=20"
ACCOUNT = "duopeier:运营"
PASSWORD = "Lxl2026@"


def login(page):
    """登录千牛卖家中心（已登录直接过）——复用 publish_auto 的登录逻辑"""
    try:
        if page.locator("span.next-btn-helper:has-text('发布商品')").count() > 0:
            print("[登录] 已登录（发布商品按钮在）")
            return True
    except Exception:
        pass
    for _ in range(2):
        need, lf = False, None
        for fr in page.frames:
            try:
                if fr.locator("#fm-login-id").count() > 0:
                    need, lf = True, fr
                    break
            except Exception:
                continue
        if not need:
            try:
                if page.locator("span.next-btn-helper:has-text('发布商品')").count() > 0:
                    print("[登录] 已在搜索页")
                    return True
            except Exception:
                pass
            print("[登录] 无登录框（视为已登录）")
            return True
        try:
            lf.fill("#fm-login-id", ACCOUNT)
            lf.fill("#fm-login-password", PASSWORD)
            try:
                cb = lf.locator("input[type='checkbox']").first
                if cb.count() > 0 and not cb.is_checked():
                    cb.click()
            except Exception:
                pass
            lf.click("button:has-text('登录')")
            print("[登录] 已填账号密码并登录")
            time.sleep(4)
            try:
                if page.locator("#queryItemId").count() == 0:
                    page.goto(SELL_URL, timeout=60000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
            except Exception:
                pass
            return True
        except Exception as e:
            print("[登录] 异常:", str(e)[:60])
            return False
    return False
