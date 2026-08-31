# -*- coding: utf-8 -*-
"""MTOP API 客户端（skill 自包含版）——不依赖外部项目文件
- 登录逻辑内嵌（不再 import publish_auto）
- chrome profile 用 skill 内 .profile（首次运行自动登录）
- 运行环境：任意装有 playwright 的 python（API 工具不需要 numpy）
用法：
    from _mtop_api import MtopClient
    mc = MtopClient().open()       # 首次运行会弹浏览器登录（自动填账号）
    items = mc.search_items("料号") # [{itemId,title,price}]
    mc.close()
"""
import os
import sys
import json
import time
import hashlib
import urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DIR = os.path.join(BASE, ".profile")      # skill 内 profile（登录态）
RUNTIME_DIR = os.path.join(BASE, "runtime")
APPKEY = "12574478"
H5API = "https://h5api.m.taobao.com/h5/{api}/{v}/"
SELL_URL = "https://myseller.taobao.com/home.htm/SellManage/on_sale?current=1&pageSize=20"
# 登录账号（千牛卖家中心）
ACCOUNT = "duopeier:运营"
PASSWORD = "Lxl2026@"


def find_chrome():
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Users\jdt-pty\AppData\Local\Google\Chrome\Application\chrome.exe"):
        if os.path.isfile(p):
            return p
    return None


class MtopClient:
    def __init__(self, profile=None, chrome=None):
        self.PROFILE = profile or PROFILE_DIR
        self.CHROME = chrome or find_chrome() or "chrome"
        self.p = None
        self.ctx = None
        self.page = None
        self.token = ""
        os.makedirs(RUNTIME_DIR, exist_ok=True)

    def open(self):
        from playwright.sync_api import sync_playwright
        self.p = sync_playwright().start()
        self.ctx = self.p.chromium.launch_persistent_context(
            self.PROFILE, executable_path=self.CHROME, headless=False,
            viewport={"width": 1400, "height": 900}, locale="zh-CN",
            args=["--disable-blink-features=AutomationControlled"])
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        self.page.goto(SELL_URL, timeout=60000, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)
        self._login()
        self.page.wait_for_timeout(2500)
        self._refresh_token()
        print("[mtop] 就绪（token=%s...）" % self.token[:16])
        return self

    def _login(self):
        """内嵌登录：检测登录框 → 填账号密码 → 登录（已登录直接过）"""
        try:
            if self.page.locator("span.next-btn-helper:has-text('发布商品')").count() > 0:
                print("[登录] 已登录（发布商品按钮在）")
                return
        except Exception:
            pass
        for _ in range(2):
            need, lf = False, None
            for fr in self.page.frames:
                try:
                    if fr.locator("#fm-login-id").count() > 0:
                        need, lf = True, fr
                        break
                except Exception:
                    continue
            if not need:
                print("[登录] 已登录")
                return
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
                    self.page.goto(SELL_URL, timeout=60000, wait_until="domcontentloaded")
                    self.page.wait_for_timeout(2000)
                except Exception:
                    pass
                return
            except Exception as e:
                print("[登录] 异常:", str(e)[:60])
                return

    def _refresh_token(self):
        for c in self.ctx.cookies():
            if c["name"] == "_m_h5_tk":
                self.token = c["value"]
                break

    def _sign(self, t, data_str):
        tk = self.token.split("_")[0] if self.token else ""
        return hashlib.md5(("%s&%s&%s&%s" % (tk, t, APPKEY, data_str)).encode("utf-8")).hexdigest()

    def call(self, api, data_obj, v="1.0"):
        """页面内 fetch 直调 MTOP——返回完整响应 dict（绕过 RGV587）"""
        t = str(int(time.time() * 1000))
        data_str = json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False)
        sign = self._sign(t, data_str)
        qs = urllib.parse.urlencode({
            "jsv": "2.6.1", "appKey": APPKEY, "t": t, "sign": sign,
            "api": api, "v": v, "ttid": "11320@taobao_WEB_9.9.99",
            "type": "originaljson", "dataType": "json"})
        url = H5API.format(api=api, v=v) + "?" + qs
        body = urllib.parse.urlencode({"data": data_str})
        self._refresh_token()
        if not self.token:
            raise RuntimeError("无 _m_h5_tk——需重新登录")
        resp = self.page.evaluate(
            """async (a) => {
                const r = await fetch(a.u, {method: 'POST', credentials: 'include',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: a.b});
                return await r.text();
            }""", {"u": url, "b": body})
        return json.loads(resp)

    def search_items(self, kw, page=1, page_size=20):
        """商品管理搜索：料号/标题 → [{itemId,title,price,link}]"""
        data = {
            "url": "/taobao/manager/table.htm",
            "jsonBody": json.dumps({"tab": "on_sale", "pagination": {"current": page, "pageSize": page_size},
                                    "filtertab": "", "filter": {"queryTitle": kw}, "table": {}},
                                   separators=(",", ":"), ensure_ascii=False),
        }
        d = self.call("mtop.taobao.sell.pc.manage.async", data)
        ret = (d.get("ret") or [""])[0]
        if "SUCCESS" not in ret:
            return [], ret
        inner = json.loads(d["data"]["result"])
        rows = (inner.get("data") or {}).get("table", {}).get("dataSource") or []
        out = []
        for r in rows:
            desc = r.get("itemDesc") or {}
            title = ""
            for x in desc.get("desc") or []:
                if x.get("text"):
                    title = x["text"]
                    break
            price = ""
            pv = r.get("managerPrice") or {}
            if isinstance(pv, dict):
                price = pv.get("currentPrice", "")
            out.append({"itemId": str(r.get("itemId", "")), "title": str(title),
                        "price": str(price), "link": "https://item.taobao.com/item.htm?id=%s" % r.get("itemId", "")})
        return out, "SUCCESS"

    def check_dual(self, kw):
        """双百检测：搜索商品 → diagnoseInfoV3.scoreLabel == '流量加速中' 即双百
        返回 [{itemId,title,dual,basicScore,scoreLabel}]——未搜到返回 []"""
        data = {
            "url": "/taobao/manager/table.htm",
            "jsonBody": json.dumps({"tab": "on_sale", "pagination": {"current": 1, "pageSize": 20},
                                    "filtertab": "", "filter": {"queryTitle": kw}, "table": {}},
                                   separators=(",", ":"), ensure_ascii=False),
        }
        d = self.call("mtop.taobao.sell.pc.manage.async", data)
        ret = (d.get("ret") or [""])[0]
        if "SUCCESS" not in ret:
            return [], ret
        inner = json.loads(d["data"]["result"])
        rows = (inner.get("data") or {}).get("table", {}).get("dataSource") or []
        out = []
        for r in rows:
            diag = r.get("diagnoseInfoV3") or {}
            desc = r.get("itemDesc") or {}
            title = ""
            for x in (desc.get("desc") or []):
                if x.get("text"):
                    title = x["text"]
                    break
            out.append({
                "itemId": str(r.get("itemId", "")), "title": str(title),
                "dual": diag.get("scoreLabel") == "流量加速中",
                "basicScore": diag.get("basicScore"),
                "scoreLabel": diag.get("scoreLabel"),
            })
        return out, "SUCCESS"

    def close(self):
        try:
            if self.ctx:
                self.ctx.close()
        except Exception:
            pass
        try:
            if self.p:
                self.p.stop()
        except Exception:
            pass


if __name__ == "__main__":
    kw = sys.argv[1] if len(sys.argv) > 1 else "39-01-2060"
    mc = MtopClient().open()
    items, ret = mc.search_items(kw)
    print("ret:", ret)
    for it in items:
        print("  itemId:", it["itemId"], "|", it["title"][:40], "|", it["price"])
    mc.close()
