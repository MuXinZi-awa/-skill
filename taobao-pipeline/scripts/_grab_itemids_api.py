# -*- coding: utf-8 -*-
"""API 版抓 ID（利刃版）：MtopClient 搜索 → itemId，追加 新品推广_待补.csv
比浏览器版快 10 倍（登录一次查全部，0.5s/品 vs 8s/品）
用法：python _grab_itemids_api.py 料号1 料号2 ...
失败品 fallback：_grab_itemids.py（浏览器版）
"""
import sys
import os
import csv
import time

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RUNTIME = os.path.join(BASE, "runtime")
os.makedirs(RUNTIME, exist_ok=True)
sys.path.insert(0, BASE)
from _mtop_api import MtopClient

CSV = os.path.join(RUNTIME, "新品推广_待补.csv")


def load_existing():
    m = {}
    if os.path.isfile(CSV):
        for row in csv.reader(open(CSV, encoding="utf-8-sig")):
            if row and len(row) > 1:
                m[row[0]] = row[1]
    return m


def save(rows):
    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)


def main():
    lhs = [a for a in sys.argv[1:] if a and not a.startswith("-")]
    if not lhs:
        print("用法: python _grab_itemids_api.py 料号1 料号2 ...")
        return
    existing = load_existing()
    todo = [lh for lh in lhs if lh not in existing]
    print("[抓ID-API] 待抓 %d 个（已有 %d 个跳过）" % (len(todo), len(lhs) - len(todo)))
    if not todo:
        return
    mc = MtopClient().open()
    ok = fail = 0
    t0 = time.time()
    for i, lh in enumerate(todo, 1):
        try:
            items, ret = mc.search_items(lh)
            if items:
                existing[lh] = items[0]["itemId"]
                ok += 1
                print("[抓ID-API] %d/%d ✓ %s -> %s" % (i, len(todo), lh, items[0]["itemId"]))
            else:
                fail += 1
                print("[抓ID-API] %d/%d ✗ %s（%s）——fallback 浏览器版" % (i, len(todo), lh, ret[:40]))
        except Exception as e:
            fail += 1
            print("[抓ID-API] %d/%d ✗ %s 异常 %s" % (i, len(todo), lh, str(e)[:60]))
        time.sleep(0.3)
    mc.close()
    # 保存（含已有）
    rows = [[lh, vid] for lh, vid in existing.items()]
    save(rows)
    print("[抓ID-API] 完成：成功 %d / 失败 %d（%.0fs，需浏览器补抓: %d）" % (
        ok, fail, time.time() - t0, fail))


if __name__ == "__main__":
    main()
