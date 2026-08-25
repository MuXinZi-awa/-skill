# -*- coding: utf-8 -*-
"""小黑盒视觉辅助（xiaoheihe-bot-skill）——把图帖图片变成文字描述

让 Agent / 用户在遇到图片帖时不至于「被拒之门外」：
  图帖 → 拿图片 URL/文件 → 本脚本 → 视觉模型 → 图片内容描述 → 写评论/回帖

用法：
  python heihe_vision.py --url "https://cdn.xxx/1.jpg" [--url "https://.../2.jpg"]
  python heihe_vision.py --file "C:/path/to/image.png" [--file ...]
  python heihe_vision.py --url ... --prompt "自定义描述要求" --max-tokens 1024

配置（config.json → vision 块）：
  enabled / base_url / api_key(留空复用 ai.api_key) / model / detail / prompt
  视觉模型：deepseek-v4-flash-vision-exp（DeepSeek 官方，OpenAI 兼容）
"""
import sys
import os
import json
import base64
import argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_FILE = os.path.join(SKILL_DIR, "config.json")

import requests

DEFAULT_PROMPT = (
    "你是小黑盒游戏社区助手。请描述这张图片的内容：画面主体、场景、图中文字、氛围。"
    "如果与游戏相关（截图、攻略、梗图、表情包），请指出游戏与关键细节。"
    "描述要足够详细，让看不到图片的人能理解帖子内容、写出恰当的社区评论。"
)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")

EXT_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
}


def load_cfg():
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write("[错误] 读取 config.json 失败: %s\n" % e)
        sys.exit(1)


def get_vision_cfg(cfg):
    ai = cfg.get("ai", {})
    vision = cfg.get("vision", {})
    enabled = bool(vision.get("enabled", True))
    base_url = (vision.get("base_url") or ai.get("base_url")
                or "https://api.deepseek.com/v1").rstrip("/")
    api_key = vision.get("api_key") or ai.get("api_key") or ""
    model = vision.get("model") or "deepseek-v4-flash-vision-exp"
    timeout = float(vision.get("timeout_seconds") or ai.get("timeout_seconds") or 120)
    detail = vision.get("detail") or "low"
    prompt = vision.get("prompt") or DEFAULT_PROMPT
    return enabled, base_url, api_key, model, timeout, detail, prompt


def fetch_image_bytes(url, timeout=30):
    """下载图片，返回 (bytes, mime)。mime 优先取响应头，兜底按 URL 扩展名猜。"""
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not ctype or ctype == "application/octet-stream":
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        ctype = EXT_MIME.get(ext, "image/jpeg")
    return r.content, ctype


def guess_mime(path):
    ext = os.path.splitext(path)[1].lower()
    return EXT_MIME.get(ext, "image/jpeg")


def call_vision(base_url, api_key, model, timeout, detail, prompt, image_blocks,
                max_tokens=2048):
    url = base_url + "/chat/completions"
    headers = {"Content-Type": "application/json",
               "Authorization": "Bearer %s" % api_key}
    content = [{"type": "text", "text": prompt}]
    content.extend(image_blocks)
    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
        "stream": False,
    }
    r = requests.post(url, headers=headers, json=body, timeout=timeout)
    if r.status_code != 200:
        sys.stderr.write("[错误] API 返回 %s: %s\n%s\n" % (r.status_code, url, r.text[:500]))
        sys.exit(1)
    data = r.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except Exception:
        text = json.dumps(data, ensure_ascii=False)[:500]
    return text, data.get("usage", {})


def main():
    p = argparse.ArgumentParser(description="小黑盒视觉辅助：图片 → 文字描述")
    p.add_argument("--url", action="append", default=[], help="图片 URL（可多次传）")
    p.add_argument("--file", action="append", default=[], help="本地图片路径（可多次传）")
    p.add_argument("--prompt", default="", help="自定义描述要求（覆盖配置默认）")
    p.add_argument("--max-tokens", type=int, default=2048)
    a = p.parse_args()

    if not a.url and not a.file:
        p.error("至少提供一个 --url 或 --file")

    cfg = load_cfg()
    enabled, base_url, api_key, model, timeout, detail, prompt = get_vision_cfg(cfg)
    if not enabled:
        sys.stderr.write("[提示] vision.enabled = false，跳过（config.json 改回 true 启用）\n")
        sys.exit(0)
    if not api_key:
        sys.stderr.write("[错误] 缺 api_key：请在 config.json 的 ai.api_key 或 vision.api_key 配置\n")
        sys.exit(1)
    if a.prompt:
        prompt = a.prompt

    image_blocks = []
    for u in a.url:
        try:
            data, mime = fetch_image_bytes(u)
        except Exception as e:
            sys.stderr.write("[警告] 下载失败 %s: %s\n" % (u, e))
            continue
        b64 = base64.b64encode(data).decode("utf-8")
        image_blocks.append({"type": "image_url",
                             "image_url": {"url": "data:%s;base64,%s" % (mime, b64),
                                           "detail": detail}})
    for fp in a.file:
        if not os.path.isfile(fp):
            sys.stderr.write("[警告] 文件不存在: %s\n" % fp)
            continue
        with open(fp, "rb") as f:
            data = f.read()
        mime = guess_mime(fp)
        b64 = base64.b64encode(data).decode("utf-8")
        image_blocks.append({"type": "image_url",
                             "image_url": {"url": "data:%s;base64,%s" % (mime, b64),
                                           "detail": detail}})

    if not image_blocks:
        sys.stderr.write("[错误] 没有可用的图片输入\n")
        sys.exit(1)

    print("[视觉] %d 张图 → %s" % (len(image_blocks), model))
    text, usage = call_vision(base_url, api_key, model, timeout, detail, prompt,
                              image_blocks, a.max_tokens)
    print("【图片描述】")
    print(text)
    if usage:
        print("（token: %s）" % json.dumps(usage, ensure_ascii=False))


if __name__ == "__main__":
    main()
