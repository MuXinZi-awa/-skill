# -*- coding: utf-8 -*-
"""小黑盒删帖（xiaoheihe-bot-skill）

用法：python heihe_delete.py --link-id 188908465 --yes
"""
import json
import sys
import os
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
from heybox_client import HeyboxCommentClient

DELETE_PATH = "/bbs/app/link/delete"
DELETE_URL = "https://api.xiaoheihe.cn/bbs/app/link/delete"
CONFIG = os.path.join(SKILL_DIR, "config.json")


def build_client(cfg):
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(SKILL_DIR, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()
    if not cookie:
        raise RuntimeError("没有 cookie——先扫码登录（见 README）")
    return HeyboxCommentClient(
        base_url=DELETE_URL, req_path=DELETE_PATH,
        default_query=dict(req.get("default_query", {})),
        headers=dict(req.get("headers", {})),
        cookie=cookie, signer=CustomSigner(),
        timeout_seconds=int(req.get("timeout_seconds", 15)),
    )


def delete_post(client, link_id):
    keys = client.signer.get_keys(DELETE_PATH)
    params = dict(client.default_query)
    params.update({"hkey": keys.hkey, "nonce": keys.nonce, "_time": str(keys.Rtime)})
    body = {"link_id": str(link_id)}
    resp = client.session.post(DELETE_URL, params=params, data=body,
                               headers=client.headers, timeout=client.timeout_seconds)
    print("[删帖] HTTP", resp.status_code)
    try:
        d = resp.json()
        print("[删帖] 响应:", json.dumps(d, ensure_ascii=False)[:300])
        return d.get("status") == "ok"
    except Exception:
        print("[删帖] 原文:", resp.text[:300])
        return False


def main():
    p = argparse.ArgumentParser(description="小黑盒删帖（xiaoheihe-bot-skill）")
    p.add_argument("--link-id", required=True, type=int, help="要删的帖子 link_id")
    p.add_argument("--yes", action="store_true", help="确认删除（删帖不可逆）")
    a = p.parse_args()
    if not a.yes:
        print("⚠️ 删帖不可逆！确认请加 --yes")
        sys.exit(1)
    cfg = load_config(CONFIG)
    client = build_client(cfg)
    ok = delete_post(client, a.link_id)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
