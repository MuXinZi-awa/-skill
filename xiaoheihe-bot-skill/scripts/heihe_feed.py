# -*- coding: utf-8 -*-
"""小黑盒看热帖（xiaoheihe-bot-skill）——水贴/选评论目标

用法：python heihe_feed.py [--topic-id 7214] [--limit 10]
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
HB = _CFG.get("hb_project_path") or os.environ.get("XIAOHEIHE_HB") or ""
if not HB or not os.path.isdir(os.path.join(HB, "src")):
    raise RuntimeError("config.json 未配置 hb_project_path——见 README")
sys.path.insert(0, os.path.join(HB, "src"))
from config_loader import load_config
from auth_manager import HTTPAuthManager
from custom_signer import CustomSigner
from heybox_client import HeyboxCommentClient

CONFIG = os.path.join(HB, "config", "config.json")


def main():
    p = argparse.ArgumentParser(description="小黑盒热帖（xiaoheihe-bot-skill）")
    p.add_argument("--topic-id", type=int, default=0, help="话题ID（0=推荐流；7214=盒友杂谈；20588=密教模拟器）")
    p.add_argument("--limit", type=int, default=10)
    a = p.parse_args()

    cfg = load_config(CONFIG)
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(HB, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()

    client = HeyboxCommentClient(
        base_url=req["feeds"]["url"], req_path=req["feeds"]["req_path"],
        default_query=dict(req.get("default_query", {})),
        headers=dict(req.get("headers", {})),
        cookie=cookie, signer=CustomSigner(),
        timeout_seconds=int(req.get("timeout_seconds", 15)),
    )
    r = client.fetch_feed_ids(topic_id=a.topic_id or None, limit=a.limit)
    items = getattr(r, "items", []) or getattr(r, "link_ids", []) or []
    print("[热帖] %d 条:" % len(items))
    for it in items[:a.limit]:
        if not isinstance(it, dict):
            print("  %s" % it)
            continue
        link_id = it.get("link_id")
        title = it.get("title", "")
        topics = ",".join(t.get("name", "") for t in (it.get("topics") or []) if isinstance(t, dict))
        print("  %s  %s  [%s]" % (link_id, title[:36], topics[:20]))


if __name__ == "__main__":
    main()
