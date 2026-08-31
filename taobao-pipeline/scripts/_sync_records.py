# -*- coding: utf-8 -*-
"""同步上品全量汇总.csv + 待处理清单.csv（权威记录——队列过滤依据）
汇总：扫素材目录 .新品.done/.上品.done/.推广.done + 素材文件 + 品牌，按料号 upsert
待处理：缺素材品（未 done 无主图素材）→ 素材缺失；千金图标签不过 → 标签未过
用法：python _sync_records.py
"""
import csv
import os
import glob
import sys
import json

sys.stdout.reconfigure(encoding="utf-8")

MAT = r"C:\Users\jdt-pty\Desktop\OH-WorkSpace\办公室工作\素材\产品素材"
DATA = r"C:\Users\jdt-pty\Desktop\OH-WorkSpace\办公室工作\数据"
SUM_CSV = os.path.join(DATA, "上品全量汇总.csv")
ISS_CSV = os.path.join(DATA, "待处理清单.csv")
ATTR = os.path.join(DATA, "属性清单.csv")
QJ = r"F:\连接图图库\千金有货图片"
STATUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")


def load_attrs():
    brand = {}
    if os.path.isfile(ATTR):
        try:
            for row in csv.reader(open(ATTR, encoding="utf-8-sig")):
                if row and row[0].strip() and len(row) > 2 and row[2].strip():
                    brand[row[0].strip()] = row[2].strip()
        except Exception:
            pass
    return brand


def qj_find(lh, b):
    bdir = os.path.join(QJ, b)
    if not os.path.isdir(bdir):
        return []
    return [f for f in os.listdir(bdir) if lh in f][:3]


def has_main(lh):
    d = os.path.join(MAT, lh)
    return bool(glob.glob(os.path.join(d, "*_封面*.png"))
                or glob.glob(os.path.join(d, "*_白底*.png"))
                or glob.glob(os.path.join(d, "*_主图2.png")))


def sync_summary():
    """扫素材目录 .done 标记 → 汇总 upsert（保留老行）"""
    rows = []
    if os.path.isfile(SUM_CSV):
        with open(SUM_CSV, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    hdr = ["料号", "淘宝ID", "素材方案", "素材文件数", "素材文件", "属性", "上品状态", "推广状态", "问题"]
    have = {r.get("料号", "") for r in rows}
    brand = load_attrs()
    # 推广记录（tuiguang_auto 写 CSV——不写 .推广.done——汇总推广状态认这个）
    tg_record = set()
    try:
        with open(os.path.join(DATA, "推广记录.csv"), encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if row and row[0].strip() and row[0].strip() != "料号" and len(row) > 1 and row[1].strip() in ("成功", "已投放跳过"):
                    tg_record.add(row[0].strip())
    except Exception:
        pass
    # 扫所有料号目录
    dirs = [d for d in os.listdir(MAT) if os.path.isdir(os.path.join(MAT, d))]
    added = updated = 0
    for lh in sorted(dirs):
        d = os.path.join(MAT, lh)
        done_pub = os.path.isfile(os.path.join(d, ".上品.done"))
        done_xp = os.path.isfile(os.path.join(d, ".新品.done"))
        done_tg = os.path.isfile(os.path.join(d, ".推广.done"))
        fail = os.path.isfile(os.path.join(d, ".新品.fail"))
        if not (done_pub or done_xp or done_tg or fail):
            # 无标记——已有记录则清状态（防残留：1-2371035-3 删 done 后汇总还标已上品）
            if lh in have:
                for r in rows:
                    if r.get("料号") == lh:
                        r["上品状态"] = ""
                        r["推广状态"] = ""
                        r["问题"] = "未上架（标记已清）"
                        updated += 1
                        break
            continue
        files = [f for f in os.listdir(d) if not f.startswith(".")]
        issue = ""
        if fail and done_xp:
            issue = "fail标记残留（已上架）——待清"
        elif fail:
            issue = "上次失败（fail）——待确认是否已上架"
        elif done_pub and not done_tg:
            issue = "已上品——待推广"
        row = {
            "料号": lh, "淘宝ID": "", "素材方案": "",
            "素材文件数": len(files), "素材文件": ";".join(files),
            "属性": brand.get(lh, ""),
            "上品状态": "✅已上品" if (done_pub or done_xp) else "❌失败",
            "推广状态": "✅已推广" if (done_tg or lh in tg_record) else ("⏳待推广" if (done_pub or done_xp) else ""),
            "问题": issue,
        }
        if lh in have:
            # 已存在——更新状态字段（防旧状态残留）
            for r in rows:
                if r.get("料号") == lh:
                    for k in ("素材文件数", "素材文件", "属性", "上品状态", "推广状态", "问题"):
                        r[k] = row[k]
                    updated += 1
                    break
        else:
            rows.append(row)
            added += 1
    with open(SUM_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)
    print("[汇总] 共 %d 行（本次新增 %d / 更新 %d）" % (len(rows), added, updated))


def sync_issues():
    """缺素材 + 千金标签不过 + fail 品 → 待处理清单 upsert；已 done 的品先清出清单"""
    rows = []
    if os.path.isfile(ISS_CSV):
        with open(ISS_CSV, encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    if not rows or rows[0][:2] != ["料号", "类别"]:
        rows = [["料号", "类别", "问题", "建议"]]
    # 已 done 的品从清单移除（防遗留误报——1-2371035-3 案例）
    kept = [rows[0]]
    removed = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        if os.path.isfile(os.path.join(MAT, r[0].strip(), ".新品.done")) or os.path.isfile(os.path.join(MAT, r[0].strip(), ".上品.done")):
            removed.append(r[0].strip())
        else:
            kept.append(r)
    rows = kept
    idx = {r[0]: r for r in rows[1:] if r and r[0]}
    brand = load_attrs()
    # ① 缺素材品：未 done 且无主图素材
    n1 = n2 = 0
    for lh in sorted(brand):
        if os.path.isfile(os.path.join(MAT, lh, ".新品.done")):
            continue
        if has_main(lh):
            continue
        # 千金图库有没有？
        b = brand.get(lh, "")
        cand = qj_find(lh, b) if b else []
        if not cand:
            for sub in os.listdir(QJ):
                cand = qj_find(lh, sub)
                if cand:
                    break
        if cand:
            if lh not in idx:
                rows.append([lh, "标签待过", "千金有图（带水印）——标签权重验证/白底图后上品", "标签验证→pippit白底图"])
                n2 += 1
        else:
            if lh not in idx:
                rows.append([lh, "素材缺失", "图库/千金均无——需爬图（立创/1688）", "爬图后补素材上品"])
                n1 += 1
    # ② fail 品（非 done）——可能已上架（1-2371035-3 案例：fail 残留但已双百）——待确认，不催重跑（防重复上架）
    for lh in sorted(os.listdir(MAT)):
        if not os.path.isdir(os.path.join(MAT, lh)):
            continue
        if os.path.isfile(os.path.join(MAT, lh, ".新品.fail")) and not os.path.isfile(os.path.join(MAT, lh, ".新品.done")):
            if lh not in idx:
                rows.append([lh, "fail待确认", "fail标记残留——确认是否已上架（已上架→清fail写done；未上架→--redo重跑）", "查商品管理确认，防重复上架"])
                n2 += 1
    with open(ISS_CSV, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    print("[待处理] 共 %d 行（清除完成 %d / 新增 素材缺失%d 其他%d）" % (len(rows), len(removed), n1, n2))
    if removed:
        print("[待处理] 已清出（已 done）: %s" % ",".join(removed))


if __name__ == "__main__":
    sync_summary()
    sync_issues()
    print("完成")
