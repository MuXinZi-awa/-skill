from __future__ import annotations

import json
import hashlib
import base64
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qsl

import requests
try:
    import qrcode
except Exception:  # noqa: BLE001
    qrcode = None


class HTTPAuthManager:
    def __init__(self, state_file: str) -> None:
        self.state_path = Path(state_file)

    def load_cookie(self) -> str | None:
        if not self.state_path.exists():
            return None
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        cookie = str(data.get("cookie", "")).strip()
        return cookie or None

    def save_cookie(self, cookie: str, extra: dict[str, Any] | None = None) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "cookie": cookie,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _format_template(values: dict[str, Any], mapping: dict[str, Any]) -> dict[str, str]:
        out: dict[str, str] = {}
        for k, v in mapping.items():
            if isinstance(v, str):
                out[k] = v.format(**values)
            else:
                out[k] = str(v)
        return out

    @staticmethod
    def _cookies_to_header(cookie_dict: dict[str, str]) -> str:
        return "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    def login_with_api(self, auth_cfg: dict[str, Any], username: str, password: str) -> str:
        login_cfg = auth_cfg.get("login", {})
        if not login_cfg.get("enabled", False):
            raise ValueError("auth.login.enabled is false; please enable login config first")

        url = str(login_cfg.get("url", "")).strip()
        if not url:
            raise ValueError("auth.login.url is required")
        if "api.example.com" in url:
            raise ValueError("auth.login.url is still placeholder api.example.com; replace with real login API")

        method = str(login_cfg.get("method", "POST")).upper()
        query_tmpl = login_cfg.get("query", {})
        headers_tmpl = login_cfg.get("headers", {})
        body_tmpl = login_cfg.get("body_template", {})

        fmt_values = {"username": username, "password": password}
        query = self._format_template(fmt_values, query_tmpl)
        headers = self._format_template(fmt_values, headers_tmpl)
        body = self._format_template(fmt_values, body_tmpl)

        sess = requests.Session()
        resp = sess.request(method=method, url=url, params=query, data=body, headers=headers, timeout=20)
        resp.raise_for_status()

        # Prefer Set-Cookie from response.
        cookies = requests.utils.dict_from_cookiejar(sess.cookies)
        if not cookies:
            raise ValueError("login succeeded but no cookies found in response")

        cookie_header = self._cookies_to_header(cookies)
        self.save_cookie(cookie_header, extra={"login_url": url})
        return cookie_header

    @staticmethod
    def _cookies_to_dict(resp: requests.Response) -> dict[str, str]:
        out: dict[str, str] = {}
        for c in resp.cookies:
            out[c.name] = c.value
        return out

    @staticmethod
    def _build_xhh_tokenid() -> str:
        raw = bytearray()
        for seed in (str(int(time.time())), "asda", "sdaasf", "sadasdas"):
            raw.extend(hashlib.md5(seed.encode("utf-8")).digest())
        raw.append(0)
        return base64.b64encode(bytes(raw)).decode("ascii")

    def login_with_qr(
        self,
        *,
        req_cfg: dict[str, Any],
        signer: Any,
        timeout_seconds: int = 180,
        poll_interval_seconds: int = 1,
    ) -> str:
        base_api = "https://api.xiaoheihe.cn"
        default_query = dict(req_cfg.get("default_query", {}))
        headers = dict(req_cfg.get("headers", {}))
        headers.setdefault("Referer", "https://www.xiaoheihe.cn/")
        headers.setdefault("User-Agent", "Mozilla/5.0")

        sess = requests.Session()
        sess.trust_env = False

        def signed_get(path: str, extra_query: dict[str, str] | None = None, cookie: str | None = None) -> requests.Response:
            keys = signer.get_keys(path)
            params = dict(default_query)
            # Align QR login request fingerprint with xhhRobot behavior.
            params["os_type"] = "web"
            params["app"] = "web"
            params["client_type"] = "web"
            params["x_client_type"] = "web"
            params["x_app"] = "heybox_website"
            params["x_os_type"] = "Windows"
            params["device_info"] = "Chrome"
            params.update({"hkey": keys.hkey, "nonce": keys.nonce, "_time": str(keys.Rtime), "_notip": "true"})
            if extra_query:
                params.update(extra_query)
            req_headers = dict(headers)
            if cookie:
                req_headers["Cookie"] = cookie
            resp = sess.get(f"{base_api}{path}", params=params, headers=req_headers, timeout=20)
            resp.raise_for_status()
            return resp

        resp = signed_get("/account/get_qrcode_url/")
        payload = resp.json()
        qr_url = str(((payload.get("result") or {}).get("qr_url")) or "").strip()
        if not qr_url:
            raise ValueError(f"qr_url missing: {payload}")
        print(f"[QR] login url:\n{qr_url}")
        self._render_qr(qr_url)

        parsed = urlparse(qr_url)
        qr_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not qr_query:
            raise ValueError(f"invalid qr_url query: {qr_url}")

        deadline = time.time() + max(10, int(timeout_seconds))
        while time.time() < deadline:
            state_resp = signed_get("/account/qr_state/", extra_query={k: v for k, v in qr_query.items()})
            state = state_resp.json()
            result = state.get("result") if isinstance(state, dict) else {}
            err = str((result or {}).get("error", ""))
            err_msg = str((result or {}).get("error_msg", ""))
            nickname = str((result or {}).get("nickname", ""))
            print(f"[QR] state={err} msg={err_msg}")

            if err == "ok":
                cookie_map = self._cookies_to_dict(state_resp)
                if not cookie_map:
                    raise ValueError("qr login success but no cookies received")
                cookie_map.setdefault("x_xhh_tokenid", self._build_xhh_tokenid())
                cookie_header = "; ".join([f"{k}={v}" for k, v in cookie_map.items()])
                self.save_cookie(cookie_header, extra={"source": "qr_login", "nickname": nickname})
                return cookie_header

            if err.lower() in {"expired", "timeout", "cancel"}:
                raise ValueError(f"qr login terminated: {err} {err_msg}".strip())

            time.sleep(max(1, int(poll_interval_seconds)))

        raise TimeoutError(f"qr login timed out after {timeout_seconds}s")

    @staticmethod
    def _render_qr(qr_url: str) -> None:
        if qrcode is None:
            print("[QR] qrcode library not installed, cannot render terminal QR.")
            print("[QR] install with: pip install qrcode[pil]")
            return
        try:
            qr = qrcode.QRCode(border=1)
            qr.add_data(qr_url)
            qr.make(fit=True)
            matrix = qr.get_matrix()
            black = "██"
            white = "  "
            print("[QR] scan this QR with XiaoHeiHe app:")
            for row in matrix:
                print("".join(black if cell else white for cell in row))
            img = qr.make_image(fill_color="black", back_color="white")
            img.save("qrcode.png")
            print("[QR] image saved: qrcode.png")
        except Exception as exc:  # noqa: BLE001
            print(f"[QR] render failed: {exc}")
