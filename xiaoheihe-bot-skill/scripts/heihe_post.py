# -*- coding: utf-8 -*-
"""小黑盒发帖（xiaoheihe-bot-skill）

用法：
    python heihe_post.py --title "标题" --text "正文" [--topic-id 20588]
    python heihe_post.py --library [索引]    # 发帖子库（post_library.json）
    python heihe_post.py --list              # 列帖子库
    python heihe_post.py --library 0 --dry-run

依赖 heibox-comment-bot 项目（签名/cookie），路径在 config.json 的 hb_project_path 配置。
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
from heybox_client import HeyboxCommentClient

LOG_FILE = _CFG.get("log_file") or ""


def log_action(action, link_id, title, topic):
    if not LOG_FILE:
        return
    try:
        os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
        line = "- %s | %s | link %s | 《%s》 | 分区:%s\n" % (
            time.strftime("%m-%d %H:%M"), action, link_id, title[:30], topic)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


POST_PATH = "/bbs/app/api/link/post"
POST_URL = "https://api.xiaoheihe.cn/bbs/app/api/link/post"
CONFIG = os.path.join(SKILL_DIR, "config.json")
LIBRARY = os.path.join(SKILL_DIR, "post_library.json")


def build_client(cfg):
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    am = HTTPAuthManager(os.path.join(SKILL_DIR, st))
    cookie = am.load_cookie() or ""
    if not cookie:
        cookie = str(req.get("cookie", "")).strip()
    if not cookie:
        raise RuntimeError("没有 cookie——先扫码登录 heibox-comment-bot（见 README）")
    return HeyboxCommentClient(
        base_url=POST_URL, req_path=POST_PATH,
        default_query=dict(req.get("default_query", {})),
        headers=dict(req.get("headers", {})),
        cookie=cookie, signer=CustomSigner(),
        timeout_seconds=int(req.get("timeout_seconds", 15)),
    )


def create_post(client, title, text_blocks, topic_ids="20588", desc="",
                link_tag=27, post_type=1, original=1, declaration=0, view_limit=1):
    keys = client.signer.get_keys(POST_PATH)
    params = dict(client.default_query)
    params.update({"hkey": keys.hkey, "nonce": keys.nonce, "_time": str(keys.Rtime)})
    words = sum(len(b.get("text", "")) for b in text_blocks if b.get("type") == "text")
    body = {
        "link_tag": str(link_tag),
        "text": json.dumps(text_blocks, ensure_ascii=False),
        "title": title,
        "desc": desc or "",
        "words_count": str(words),
        "hashtags": json.dumps([], ensure_ascii=False),
        "schedule_ts": "0",
        "view_limit": str(view_limit),
        "post_type": str(post_type),
        "original": str(original),
        "declaration": str(declaration),
        "topic_ids": str(topic_ids),
    }
    resp = client.session.post(POST_URL, params=params, data=body,
                               headers=client.headers, timeout=client.timeout_seconds)
    print("[发帖] HTTP", resp.status_code)
    try:
        d = resp.json()
        print("[发帖] 响应:", json.dumps(d, ensure_ascii=False)[:300])
        return d.get("status") == "ok"
    except Exception:
        print("[发帖] 原文:", resp.text[:300])
        return False


def get_image_size(url, timeout=15):
    """下载图片前若干字节解析尺寸（JPEG/PNG），失败返回 None。"""
    import struct
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        data = resp.raw.read(65536)
    except Exception:
        return None
    if not data:
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    return None


def build_img_block(img_spec):
    """--image 参数 → img 块。支持 'URL' 或 'URL,宽,高'；无尺寸时尝试下载解析。"""
    parts = img_spec.split(",")
    url = parts[0]
    w = h = None
    if len(parts) == 3:
        try:
            w, h = int(parts[1]), int(parts[2])
        except ValueError:
            w = h = None
    if w is None or h is None:
        size = get_image_size(url)
        if size:
            w, h = size
    block = {"type": "img", "url": url}
    if w and h:
        block["width"] = w
        block["height"] = h
    return block


def main():
    p = argparse.ArgumentParser(description="小黑盒发帖（xiaoheihe-bot-skill）")
    p.add_argument("--title", help="标题")
    p.add_argument("--text", help="正文")
    p.add_argument("--image", action="append", help="图片 URL 或 'URL,宽,高'（可重复；或帖子库条目的 images 字段）")
    p.add_argument("--topic-id", default="20588", help="话题/分区ID（默认 20588=密教模拟器）")
    p.add_argument("--library", nargs="?", const="0", help="发帖子库（可索引）")
    p.add_argument("--list", action="store_true", help="列帖子库")
    p.add_argument("--dry-run", action="store_true", help="只打印不发送")
    a = p.parse_args()

    if a.list:
        lib = json.load(open(LIBRARY, encoding="utf-8"))
        for i, post in enumerate(lib):
            print("[%d] %s  | 话题:%s  | 标签:%s  | 图:%d张" % (
                i, post["title"], post.get("topic_ids"), ",".join(post.get("tags", [])), len(post.get("images", []))))
        return

    cfg = load_config(CONFIG)
    images = list(a.image or [])
    if a.library is not None:
        lib = json.load(open(LIBRARY, encoding="utf-8"))
        idx = int(a.library) if a.library else 0
        post = lib[idx]
        title = post["title"]
        text = post["text"]
        topic_ids = str(post.get("topic_ids", "20588"))
        link_tag = int(post.get("link_tag", 27))
        images = images or list(post.get("images", []))
        print("[发帖] 帖子库[%d]: %s (link_tag=%d, 图:%d张)" % (idx, title, link_tag, len(images)))
    elif a.title and a.text:
        title, text, topic_ids = a.title, a.text, a.topic_id
        link_tag = 27
    else:
        print("要 --title+--text 或 --library")
        sys.exit(1)

    # 正文块：文字 + 图片（img 块带 url + width/height，服务端缺尺寸会丢图）
    text_blocks = [{"type": "text", "text": text}]
    for img_spec in images:
        text_blocks.append(build_img_block(img_spec))

    if a.dry_run:
        print("[dry-run] 标题:", title)
        print("[dry-run] 正文:", text[:80], "...")
        for b in text_blocks[1:]:
            print("[dry-run] 图:", b.get("url"), "%sx%s" % (b.get("width", "?"), b.get("height", "?")))
        return

    client = build_client(cfg)
    ok = create_post(client, title, text_blocks,
                     topic_ids=topic_ids, link_tag=link_tag)
    if ok:
        log_action("发帖", "", title, topic_ids)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
