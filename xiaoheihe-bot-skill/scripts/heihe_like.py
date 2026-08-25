# -*- coding: utf-8 -*-
"""小黑盒点赞（xiaoheihe-bot-skill）

用法：
    python heihe_like.py --comment-id 939111031          # 给评论点赞
    python heihe_like.py --link-id 188975073             # 给帖子点赞（workshopapi）

接口（2026-08-25 抓包确认）：
    评论点赞：POST /bbs/app/comment/support
        data: comment_id=<id>&support_type=1   → {"status":"ok"}
    帖子点赞：POST https://workshopapi.xiaoheihe.cn/bbs/app/profile/award/link
        data: link_id=<id>（待验证）
"""
import json
import sys
import os
import time
import argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_FILE = os.path.join(SKILL_DIR, "config.json")


def load_cfg():
    try:
        return json.load(open(CFG_FILE, encoding="utf-8"))
    except Exception:
        return {}


_CFG = load_cfg()
LIB_DIR = os.path.join(SKILL_DIR, "scripts", "lib")
sys.path.insert(0, LIB_DIR)
from config_loader import load_config
from auth_manager import HTTPAuthManager
from custom_signer import CustomSigner
import requests

CONFIG = os.path.join(SKILL_DIR, "config.json")
COMMENT_SUPPORT_PATH = "/bbs/app/comment/support"
COMMENT_SUPPORT_URL = "https://api.xiaoheihe.cn/bbs/app/comment/support"
LINK_AWARD_PATH = "/bbs/app/profile/award/link"
LINK_AWARD_URL = "https://workshopapi.xiaoheihe.cn/bbs/app/profile/award/link"


def build_session(cfg):
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(SKILL_DIR, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()
    if not cookie:
        raise RuntimeError("没有 cookie——先扫码登录（见 README）")
    headers = dict(req.get("headers", {}))
    headers["Cookie"] = cookie
    dq = dict(req.get("default_query", {}))
    dq.pop("device_info", None)
    dq.pop("device_id", None)
    dq["x_client_version"] = ""
    dq["web_version"] = "3.0"
    dq.pop("heybox_id", None)  # comment/support 抓包无 heybox_id
    # 当前账号 heybox_id 从 cookie 解析（user_heybox_id）
    heybox_id = ""
    for p in cookie.split("; "):
        if p.startswith("user_heybox_id="):
            heybox_id = p.split("=", 1)[1].strip()
            break
    session = requests.Session()
    session.trust_env = False
    return session, headers, dq, CustomSigner(), heybox_id


def main():
    p = argparse.ArgumentParser(description="小黑盒点赞（xiaoheihe-bot-skill）")
    p.add_argument("--comment-id", type=int, help="要赞的评论 comment_id")
    p.add_argument("--link-id", type=int, help="要赞的帖子 link_id（接口待验证）")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if not a.comment_id and not a.link_id:
        print("请指定 --comment-id（评论）或 --link-id（帖子）")
        sys.exit(1)

    cfg = load_config(CONFIG)
    session, headers, dq, signer, heybox_id = build_session(cfg)

    if a.comment_id:
        path = COMMENT_SUPPORT_PATH
        keys = signer.get_keys(path)
        params = dict(dq)
        params.update({"hkey": keys.hkey, "nonce": keys.nonce, "_time": str(keys.Rtime), "_notip": "true"})
        body = {"comment_id": str(a.comment_id), "support_type": "1"}
        if a.dry_run:
            print("[dry-run] 赞评论 %s" % a.comment_id)
            return
        resp = session.post(COMMENT_SUPPORT_URL, params=params, data=body, headers=headers, timeout=15)
        print("[点赞] HTTP", resp.status_code)
        try:
            d = resp.json()
            print("[点赞] 响应:", json.dumps(d, ensure_ascii=False)[:200])
            ok = d.get("status") == "ok"
        except Exception:
            print("[点赞] 原文:", resp.text[:200])
            ok = False
        sys.exit(0 if ok else 1)
    else:
        # 帖子点赞（2026-08-25 梓帆抓包破译）：POST workshopapi /bbs/app/profile/award/link
        # query: app/os_type/x_app/x_client_type/x_os_type/x_client_version/client_type/web_version/version + heybox_id + hkey/_time/nonce
        # body: link_id=<id>&award_type=1
        if not heybox_id:
            print("[错误] cookie 里没有 user_heybox_id——请重新扫码登录")
            sys.exit(1)
        path = LINK_AWARD_PATH
        keys = signer.get_keys(path)
        params = dict(dq)
        params["heybox_id"] = heybox_id
        params.update({"hkey": keys.hkey, "nonce": keys.nonce, "_time": str(keys.Rtime), "_notip": "true"})
        body = {"link_id": str(a.link_id), "award_type": "1"}
        if a.dry_run:
            print("[dry-run] 赞帖子 %s (heybox_id=%s)" % (a.link_id, heybox_id))
            print("[dry-run] POST", LINK_AWARD_URL)
            print("[dry-run] params:", json.dumps(params, ensure_ascii=False))
            print("[dry-run] body:", json.dumps(body))
            return
        resp = session.post(LINK_AWARD_URL, params=params, data=body, headers=headers, timeout=15)
        print("[点赞] HTTP", resp.status_code)
        try:
            d = resp.json()
            print("[点赞] 响应:", json.dumps(d, ensure_ascii=False)[:200])
            ok = d.get("status") == "ok"
        except Exception:
            print("[点赞] 原文:", resp.text[:200])
            ok = False
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
