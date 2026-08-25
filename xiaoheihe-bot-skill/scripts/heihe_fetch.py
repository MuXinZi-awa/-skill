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


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
IMAGE_HOST_HINTS = ("/img/", "/image/", "/pic/", "/photo/", "cdn", "heybox")


def looks_like_image(s: str) -> bool:
    """启发式判断：像图片 URL 的字符串（宽匹配，不怕字段名变化）"""
    if not isinstance(s, str):
        return False
    low = s.lower()
    if not low.startswith("http"):
        return False
    if 10 <= len(s) <= 8192:
        if low.rstrip("?").rstrip("/").endswith(IMAGE_EXTS):
            return True
        if any(h in low for h in IMAGE_HOST_HINTS):
            # 有图片域名/路径特征且不带明显 query 的，收下
            if "?" not in low or any(h in low.split("?")[0] for h in IMAGE_HOST_HINTS):
                return True
    return False


def find_image_urls(obj, out=None):
    """递归遍历 API 返回结构，收集所有像图片 URL 的字符串"""
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for v in obj.values():
            find_image_urls(v, out)
    elif isinstance(obj, list):
        for it in obj:
            find_image_urls(it, out)
    elif looks_like_image(obj):
        out.add(obj)
    return sorted(out)


def main():
    p = argparse.ArgumentParser(description="小黑盒看帖（xiaoheihe-bot-skill）")
    p.add_argument("--link-id", required=True, type=int)
    p.add_argument("--with-comments", action="store_true", help="同时查看评论区")
    p.add_argument("--limit", type=int, default=10, help="最多打印评论条数（默认10）")
    p.add_argument("--images", action="store_true", help="列出帖子里发现的图片 URL（图帖用，配合 heihe_vision.py）")
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
    data = getattr(r, "raw", None) or getattr(r, "data", None) or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            data = {}

    print("[看帖] %s:" % a.link_id)
    content = client._extract_link_content(data)
    if content:
        print("【正文】", content[:800])
    else:
        print("（正文获取失败，原始数据前 500 字：）")
        print(json.dumps(data, ensure_ascii=False)[:500])

    if a.images:
        imgs = find_image_urls(data)
        print("【图片】共 %d 张:" % len(imgs))
        for i, u in enumerate(imgs, 1):
            print("  %d. %s" % (i, u))
        if imgs:
            print("（用 python scripts\\heihe_vision.py --url \"<URL>\" 查看图片内容）")

    if a.with_comments:
        comments = client._extract_comments(data)
        print("【评论】共 %d 条（显示前 %d 条）:" % (len(comments), a.limit))
        for c in comments[:a.limit]:
            name = c.get("username") or "?"
            text = (c.get("text") or "")[:120]
            floor = c.get("floor_num") or ""
            print("  %s楼 %s: %s" % (floor, name, text))


if __name__ == "__main__":
    main()
