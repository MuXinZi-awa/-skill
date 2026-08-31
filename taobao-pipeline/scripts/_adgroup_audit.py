# -*- coding: utf-8 -*-
"""万相台广告组出价审计（读操作）：findPage 拉全广告组 → 逐个 bidword/findList 查出价
输出：runtime/adgroup_bids.csv（adgroupId,名称,关键词,bidPrice,状态）+ 错价统计
用法：python _adgroup_audit.py [--campaign 计划ID] [--pages 4]
"""
import os
import sys
import json
import time
import re
import csv

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(BASE, "runtime")
os.makedirs(RUNTIME, exist_ok=True)
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(BASE, ".profile")
TG_URL = "https://one.alimama.com/index.html?spm=a21dvs.28490323.cubeComp-1446-93204762-239-.dfde9da63_CAMPAIGN_FINISH.2b021130oB18GG#!/manage/search-detail?bizCode=onebpSearch&campaignId=72264315693&tab=adgroup&spm="
OUT = os.path.join(BASE, "runtime", "adgroup_bids.csv")
CAMPAIGN = 72264315693


def main():
    pages = 4
    for i, a in enumerate(sys.argv):
        if a == "--pages" and i + 1 < len(sys.argv):
            pages = int(sys.argv[i + 1])
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
        except Exception as e:
            print("[审计] 登录异常:", str(e)[:60])
        page.wait_for_timeout(3000)
        csrf = {"v": ""}
        page.on("request", lambda req: csrf.update(
            {"v": re.search(r"csrfId=([0-9a-f_]+)", req.url).group(1)}
            if re.search(r"csrfId=([0-9a-f_]+)", req.url) and not csrf["v"] else {}))
        page.goto(TG_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(10000)
        print("[审计] csrfId:", csrf["v"][:40])

        def call(url, body, pause=0.35):
            r = page.evaluate("""async (a) => {
                const r = await fetch(a.u, {method: 'POST', credentials: 'include',
                    headers: {'Content-Type': 'application/json', 'x-requested-with': 'XMLHttpRequest'},
                    body: JSON.stringify(a.b)});
                return await r.text();
            }""", {"u": url, "b": body})
            time.sleep(pause)  # 低频防风控
            return r

        # 1) offset 翻页拉全广告组（真实参数：campaignIdList + offset + pageSize——pageNum 不生效）
        adgroups = []
        seen_ids = set()
        for off in range(0, 500, 100):
            u = "https://one.alimama.com/adgroup/horizontal/findPage.json?csrfId=%s&bizCode=onebpSearch" % csrf["v"]
            b = {"bizCode": "onebpSearch", "campaignIdList": [str(CAMPAIGN)], "offset": off,
                 "pageSize": 100, "statusList": ["start", "pause"], "csrfId": csrf["v"]}
            r = json.loads(call(u, b))
            lst = (r.get("data") or {}).get("list") or []
            new_n = 0
            for g in lst:
                gid = g.get("adgroupId")
                if gid in seen_ids:
                    continue
                seen_ids.add(gid)
                adgroups.append({"adgroupId": gid, "name": g.get("adgroupName") or "",
                                 "status": g.get("displayStatus") or ""})
                new_n += 1
            print("[审计] offset=%d 本页%d 新增%d（累计 %d）" % (off, len(lst), new_n, len(adgroups)))
            if len(lst) < 100:
                break
        print("[审计] 共 %d 个广告组（唯一）" % len(adgroups))

        # 2) 逐个查关键词出价（campaignIdList + adgroupIdList 外层——已验证）
        rows = []
        err = 0
        for i, g in enumerate(adgroups, 1):
            u2 = "https://one.alimama.com/bidword/findList.json?csrfId=%s&bizCode=onebpSearch" % csrf["v"]
            b2 = {"campaignIdList": [CAMPAIGN], "adgroupIdList": [g["adgroupId"]], "data": {}}
            try:
                r2 = json.loads(call(u2, b2, pause=0.22))
                kws = (r2.get("data") or {}).get("list") or []
                if kws:
                    for kw in kws:
                        rows.append([g["adgroupId"], g["name"], kw.get("word", ""),
                                     kw.get("bidPrice", ""), kw.get("bidwordId", ""), kw.get("status", "")])
                else:
                    rows.append([g["adgroupId"], g["name"], "", "", "", "无关键词"])
            except Exception as e:
                err += 1
                rows.append([g["adgroupId"], g["name"], "ERR", str(e)[:40], "", ""])
            if i % 50 == 0:
                print("[审计] %d/%d 已查（错误 %d）" % (i, len(adgroups), err))
        with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["adgroupId", "广告组名", "关键词", "出价", "bidwordId", "状态"])
            w.writerows(rows)
        ctx.close()

    # 3) 统计
    from collections import Counter
    bids = Counter()
    for r in rows:
        b = r[3]
        bids[str(b)] += 1
    print("\n=== 出价分布 ===")
    for b, n in bids.most_common():
        print("  %-8s %d 个" % (b, n))
    weird = [r for r in rows if r[3] not in ("0.3", "0.30", "") and r[3] != "ERR"]
    print("\n疑似错价（非 0.3）: %d 个 -> %s" % (len(weird), OUT))
    for r in weird[:15]:
        print("  ", r[0], r[1][:30], "|", r[2], "|", r[3])


if __name__ == "__main__":
    main()
