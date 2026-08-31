# -*- coding: utf-8 -*-
"""批次流水线总装：上品 → 抓ID → 推广 → 同步汇总（一条龙，无人值守）
流程：_xinpin_shangpin（上品）→ 读 status.json 成功品 → _grab_itemids（抓ID）
      → 生成推广表 → tuiguang_auto（推广）→ _sync_records（汇总/待处理同步）
用法：python _batch_pipeline.py [--limit N] [--only 料号1,料号2] [--skip-shangpin]
      --skip-shangpin：只做"抓ID+推广+同步"（上品已完成时用）
"""
import subprocess
import sys
import os
import csv
import json
import time

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.abspath(__file__))
RT = os.path.join(BASE, "runtime", "python.exe")
PY = RT if os.path.isfile(RT) else sys.executable
STATUS = os.path.join(BASE, "status.json")
GRAB_CSV = os.path.join(BASE, "新品推广_待补.csv")


def run(script, args, log_name, timeout=7200):
    log = os.path.join(BASE, "runtime", log_name)
    print("\n[流水线] 运行 %s %s -> %s" % (os.path.basename(script), " ".join(args), log_name))
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([PY, script] + args, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    tail = []
    try:
        lines = open(log, encoding="utf-8", errors="ignore").readlines()
        tail = lines[-6:]
    except Exception:
        pass
    for t in tail:
        print("   | " + t.rstrip()[:110])
    print("[流水线] rc=%d" % r.returncode)
    return r.returncode


def read_success_items():
    """读 status.json 本批成功品（status ✅）"""
    try:
        with open(STATUS, encoding="utf-8") as f:
            st = json.load(f)
        return [it["liaohao"] for it in st.get("items", []) if it.get("status") == "✅"]
    except Exception:
        return []


def read_grab_ids(lhs):
    """从抓取 CSV 读料号→ID"""
    m = {}
    if os.path.isfile(GRAB_CSV):
        for row in csv.reader(open(GRAB_CSV, encoding="utf-8-sig")):
            if row and len(row) > 1 and row[0] in lhs:
                m[row[0]] = row[1]
    return m


def main():
    argv = [a for a in sys.argv[1:]]
    skip_sp = "--skip-shangpin" in argv
    if skip_sp:
        argv.remove("--skip-shangpin")
    t0 = time.time()

    # 阶段1：上品
    if not skip_sp:
        rc = run(os.path.join(BASE, "_xinpin_shangpin.py"), argv, "pipe_shangpin.log")
        if rc != 0:
            print("[流水线] ⚠ 上品异常 rc=%d——继续后续阶段（看 pipe_shangpin.log）" % rc)
    else:
        print("[流水线] --skip-shangpin：跳过上品，直接抓ID+推广")

    # 阶段2：成功品 → 抓 ID（API 版优先——登录一次查全部，0.5s/品；失败 fallback 浏览器版）
    ok_lhs = read_success_items()
    if not ok_lhs:
        print("[流水线] ⚠ 无成功品（status.json 空）——终止")
        return
    print("\n[流水线] 本批成功 %d 个: %s" % (len(ok_lhs), ok_lhs))
    print("[流水线] 阶段2 抓 ID（API 版）...")
    rc = run(os.path.join(BASE, "_grab_itemids_api.py"), ok_lhs, "pipe_grab_api.log", timeout=1800)
    ids = read_grab_ids(ok_lhs)
    missing = [lh for lh in ok_lhs if lh not in ids]
    if missing:
        print("[流水线] API 未抓到 %d 个——浏览器版 fallback: %s" % (len(missing), missing))
        run(os.path.join(BASE, "_grab_itemids.py"), missing, "pipe_grab_fb.log", timeout=1800)
        ids = read_grab_ids(ok_lhs)
        missing = [lh for lh in ok_lhs if lh not in ids]
    if missing:
        print("[流水线] ⚠ 仍缺 ID: %s（看日志）" % missing)

    # 阶段3：推广表 → 推广
    tg_lhs = [lh for lh in ok_lhs if lh in ids]
    if tg_lhs:
        tg_csv = os.path.join(BASE, "流水线推广.csv")
        with open(tg_csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["料号", "淘宝ID"])
            for lh in tg_lhs:
                w.writerow([lh, ids[lh]])
        print("\n[流水线] 阶段3 推广 %d 个..." % len(tg_lhs))
        run(os.path.join(BASE, "tuiguang_auto.py"), ["--excel", tg_csv], "pipe_tuiguang.log", timeout=3600)
    else:
        print("\n[流水线] ⚠ 无推广品（ID 未抓到）——跳过推广")

    # 阶段4：同步汇总/待处理
    print("\n[流水线] 阶段4 同步汇总/待处理...")
    run(os.path.join(BASE, "_sync_records.py"), [], "pipe_sync.log", timeout=300)

    print("\n[流水线] ✅ 全流程完成（%.0f 分钟）——上品%d 推广%d" % (
        (time.time() - t0) / 60, len(ok_lhs), len(tg_lhs)))


if __name__ == "__main__":
    main()
