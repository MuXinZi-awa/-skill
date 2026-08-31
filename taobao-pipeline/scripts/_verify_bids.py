# -*- coding: utf-8 -*-
"""读回验证：38 个改动过的广告组 → 逐个查当前出价，确认全为 0.3
用法：python _verify_bids.py
"""
import os
import sys
import json
import time
import re

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(BASE, "runtime")
os.makedirs(RUNTIME, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(BASE, ".profile")
TG_URL = "https://one.alimama.com/index.html?spm=a21dvs.28490323.cubeComp-1446-93204762-239-.dfde9da63_CAMPAIGN_FINISH.2b021130oB18GG#!/manage/search-detail?bizCode=onebpSearch&campaignId=72264315693&tab=adgroup&spm="

from playwright.sync_api import sync_playwright
from _skill_common import SELL_URL, PROFILE, login as qn_login

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, executable_path=CHROME, headless=False,
        viewport={"width": 1500, "height": 950}, locale="zh-CN",
        args=["--disable-blink-features=AutomationControlled"])
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(SELL_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    try:
        qn_login(page)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    csrf = {"v": ""}
    page.on("request", lambda req: csrf.update(
        {"v": re.search(r"csrfId=([0-9a-f_]+)", req.url).group(1)}
        if re.search(r"csrfId=([0-9a-f_]+)", req.url) and not csrf["v"] else {}))
    page.goto(TG_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(12000)
    print("[验] csrf:", csrf["v"][:20])

    def call(url, body):
        return page.evaluate("""async (a) => { const r = await fetch(a.u, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json','x-requested-with':'XMLHttpRequest'}, body: JSON.stringify(a.b)}); return await r.text(); }""", {"u": url, "b": body})

    todo = json.load(open(os.path.join(BASE, "runtime", "fix_bid_todo.json"), encoding="utf-8"))
    ids = [int(it["adgroupId"]) for it in todo]
    ids += [82910443612, 82910505525, 83053930482]  # 手动改的 3 个
    u = "https://one.alimama.com/bidword/findList.json?csrfId=%s&bizCode=onebpSearch" % csrf["v"]
    bad = []
    ok = 0
    for i, gid in enumerate(ids, 1):
        b = {"campaignIdList": ["72264315693"], "adgroupIdList": [gid], "data": {}}
        try:
            r = call(u, b)
            d = json.loads(r)
            lst = (d.get("data") or {}).get("list") or []
            bp = lst[0].get("bidPrice") if lst else "无关键词"
            if str(bp) in ("0.3", "0.30"):
                ok += 1
            else:
                bad.append((gid, bp))
                print("[验] ✗ %s = %s" % (gid, bp))
        except Exception as e:
            bad.append((gid, "ERR"))
            print("[验] ✗ %s ERR %s" % (gid, str(e)[:50]))
        time.sleep(0.25)
    print("\n[验] 验证 %d 个：正常 0.3 = %d / 异常 = %d" % (len(ids), ok, len(bad)))
    for x in bad:
        print("  异常:", x)
    ctx.close()
