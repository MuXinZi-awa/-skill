# -*- coding: utf-8 -*-
"""小黑盒看帖内容（xiaoheihe-bot-skill）——评论/留言前先读帖

用法：python heihe_fetch.py --link-id 188908465
"""
import sys
import os
import json
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

CONFIG = os.path.join(SKILL_DIR, "config.json")


def main():
    p = argparse.ArgumentParser(description="小黑盒看帖（xiaoheihe-bot-skill）")
    p.add_argument("--link-id", required=True, type=int)
    a = p.parse_args()

    cfg = load_config(CONFIG)
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(SKILL_DIR, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()

    tree = req["link_tree"]
    client = HeyboxCommentClient(
        base_url=tree["url"], req_path=tree["req_path"],
        default_query=dict(req.get("default_query", {})),
        headers=dict(req.get("headers", {})),
        cookie=cookie, signer=CustomSigner(),
        timeout_seconds=int(req.get("timeout_seconds", 15)),
    )
    r = client.fetch_post_content(link_id=a.link_id, page=1, index=1, limit=20)
    print("[看帖] %s:" % a.link_id)
    try:
        raw = getattr(r, "raw", None) or getattr(r, "data", None)
        if raw:
            print(json.dumps(raw, ensure_ascii=False)[:1500])
        else:
            print(str(r)[:1500])
    except Exception:
        print(str(r)[:1500])


if __name__ == "__main__":
    main()
