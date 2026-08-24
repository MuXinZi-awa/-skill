# -*- coding: utf-8 -*-
"""小黑盒扫码登录（xiaoheihe-bot-skill）

用法：
    python heihe_login.py [--timeout 180]

手机小黑盒 App 扫终端二维码（或保存的 qrcode.png），登录态自动保存到 state/auth_state.json。
自包含：使用 scripts/lib 内置的签名/cookie 实现，不依赖外部项目。
"""
import os
import sys
import argparse

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(SKILL_DIR, "scripts", "lib")
sys.path.insert(0, LIB_DIR)

from config_loader import load_config
from auth_manager import HTTPAuthManager
from custom_signer import CustomSigner

CONFIG = os.path.join(SKILL_DIR, "config.json")


def main():
    p = argparse.ArgumentParser(description="小黑盒扫码登录（自包含版）")
    p.add_argument("--timeout", type=int, default=180, help="二维码超时秒数（默认180）")
    p.add_argument("--poll-interval", type=int, default=1, help="轮询间隔秒数（默认1）")
    a = p.parse_args()

    cfg = load_config(CONFIG)
    req = cfg["request"]
    st = cfg["auth"].get("state_file", "state/auth_state.json")
    state_path = os.path.join(SKILL_DIR, st)
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)

    am = HTTPAuthManager(state_path)
    signer = CustomSigner()
    am.login_with_qr(
        req_cfg=req,
        signer=signer,
        timeout_seconds=a.timeout,
        poll_interval_seconds=a.poll_interval,
    )
    print(f"[OK] 登录态已保存到 {state_path}")


if __name__ == "__main__":
    main()
