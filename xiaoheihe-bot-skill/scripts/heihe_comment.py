# -*- coding: utf-8 -*-
"""小黑盒评论（xiaoheihe-bot-skill）

用法：python heihe_comment.py --link-id 181177992 --text "评论内容"
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
HB = _CFG.get("hb_project_path") or os.environ.get("XIAOHEIHE_HB") or ""
if not HB or not os.path.isdir(os.path.join(HB, "src")):
    raise RuntimeError("config.json 未配置 hb_project_path——见 README")
sys.path.insert(0, os.path.join(HB, "src"))
from config_loader import load_config
from auth_manager import HTTPAuthManager
from custom_signer import CustomSigner
from heybox_client import HeyboxCommentClient

LOG_FILE = _CFG.get("log_file") or ""


def log_action(action, link_id, text):
    if not LOG_FILE:
        return
    try:
        os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
        line = "- %s | %s | link %s | %s\n" % (time.strftime("%m-%d %H:%M"), action, link_id, text[:40])
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


COMMENT_PATH = "/bbs/app/comment/create"
COMMENT_URL = "https://api.xiaoheihe.cn/bbs/app/comment/create"
CONFIG = os.path.join(HB, "config", "config.json")


def build_client(cfg):
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(HB, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()
    if not cookie:
        raise RuntimeError("没有 cookie——先扫码登录（见 README）")
    return HeyboxCommentClient(
        base_url=COMMENT_URL, req_path=COMMENT_PATH,
        default_query=dict(req.get("default_query", {})),
        headers=dict(req.get("headers", {})),
        cookie=cookie, signer=CustomSigner(),
        timeout_seconds=int(req.get("timeout_seconds", 15)),
    )


def main():
    p = argparse.ArgumentParser(description="小黑盒评论（xiaoheihe-bot-skill）")
    p.add_argument("--link-id", required=True, type=int, help="帖子 link_id")
    p.add_argument("--text", required=True, help="评论内容")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.dry_run:
        print("[dry-run] 评论 %s: %s" % (a.link_id, a.text[:60]))
        return
    cfg = load_config(CONFIG)
    client = build_client(cfg)
    r = client.create_comment(link_id=a.link_id, text=a.text)
    print("[评论] HTTP", getattr(r, "http_status", "?"))
    print("[评论] 结果:", getattr(r, "status", "?"))
    if getattr(r, "status", "") == "ok":
        log_action("评论", a.link_id, a.text)
    sys.exit(0 if getattr(r, "status", "") == "ok" else 1)


if __name__ == "__main__":
    main()
