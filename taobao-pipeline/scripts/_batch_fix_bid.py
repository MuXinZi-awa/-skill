# -*- coding: utf-8 -*-
"""批量改价：35 个错价 → 0.3（bidword/update.json）
读 fix_bid_todo.json → 逐个 update → 低频（0.4s/个）→ 输出结果
用法：python _batch_fix_bid.py
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
TODO = os.path.join(BASE, "runtime", "fix_bid_todo.json")

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
    csrf = {"v": "", "lp": ""}
    def grab(req):
        m = re.search(r"csrfId=([0-9a-f_]+)", req.url)
        if m and not csrf["v"]:
            csrf["v"] = m.group(1)
        m2 = re.search(r"loginPointId[\"']?:?[\"']?([0-9a-z]+)", req.post_data or "")
        if m2 and not csrf["lp"]:
            csrf["lp"] = m2.group(1)
    page.on("request", grab)
    page.goto(TG_URL, timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(12000)
    page.evaluate("""() => { const a = document.querySelector("a[href*='adgroupId=82910535634']"); if (a) a.click(); }""")
    page.wait_for_timeout(9000)
    print("[批] csrf:", csrf["v"][:20], "| lp:", csrf["lp"][:20])

    def call(url, body):
        return page.evaluate("""async (a) => { const r = await fetch(a.u, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json','x-requested-with':'XMLHttpRequest'}, body: JSON.stringify(a.b)}); return await r.text(); }""", {"u": url, "b": body})

    todo = json.load(open(TODO, encoding="utf-8"))
    print("[批] 待改 %d 个 → 0.3" % len(todo))
    u = "https://one.alimama.com/bidword/update.json?csrfId=%s&bizCode=onebpSearch" % csrf["v"]
    ok_n = fail_n = 0
    fails = []
    for i, it in enumerate(todo, 1):
        body = {
            "bizCode": "onebpSearch",
            "bidwordList": [{
                "campaignId": 72264315693, "adgroupId": int(it["adgroupId"]),
                "bidwordId": int(it["bidwordId"]), "bidPrice": 0.3,
                "bidStrategyInfo": {"status": 0},
            }],
            "csrfId": csrf["v"], "loginPointId": csrf["lp"],
        }
        try:
            r = call(u, body)
            d = json.loads(r)
            ok = (d.get("info") or {}).get("ok") is True and (d.get("data") or {}).get("count", 0) >= 1
            if ok:
                ok_n += 1
                print("[批] %d/%d ✓ %s %s → 0.3" % (i, len(todo), it["adgroupId"], it["word"]))
            else:
                fail_n += 1
                fails.append(it["adgroupId"])
                print("[批] %d/%d ✗ %s %s: %s" % (i, len(todo), it["adgroupId"], it["word"], r[:120]))
        except Exception as e:
            fail_n += 1
            fails.append(it["adgroupId"])
            print("[批] %d/%d ✗ %s 异常 %s" % (i, len(todo), it["adgroupId"], str(e)[:60]))
        time.sleep(0.4)
    print("\n[批] 完成：成功 %d / 失败 %d" % (ok_n, fail_n))
    if fails:
        print("[批] 失败清单:", fails)
    ctx.close()
