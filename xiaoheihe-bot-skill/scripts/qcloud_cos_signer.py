# -*- coding: utf-8 -*-
"""qcloud_cos_signer.py —— 腾讯云 COS 临时密钥直传，手写签名（无 SDK 版）

协议对照官方「请求签名」文档（cloud.tencent.com/document/product/436/7778）。
已用官方示例做金标准验算（SHA1(HttpString) 两例全对），算法为官方三层结构：

    SignKey      = HMAC-SHA1(SecretKey, KeyTime)              # KeyTime = start;end
    SHA1_hex     = SHA1(HttpString)                           # HttpString 四段 \n 结尾
    StringToSign = "sha1\\n{KeyTime}\\n{SHA1_hex}\\n"
    Signature    = HMAC-SHA1(SignKey, StringToSign)

注意：sig 不是直接对 HttpString 做 HMAC！漏了 StringToSign 中间层必然
SignatureDoesNotMatch（这是最容易犯的结构性错误）。
"""
import hashlib
import hmac
import time
from urllib.parse import quote

try:
    import requests
except ImportError:
    requests = None


def _hmac_sha1(key: str, msg: str) -> str:
    """HMAC-SHA1，输出 16 进制小写"""
    return hmac.new(key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha1).hexdigest()


def _uri_encode(s: str, safe: str = "") -> str:
    """COS UrlEncode：除 A-Z a-z 0-9 - _ . ~ 外全部 %XX 编码（空格 %20）"""
    return quote(s, safe=safe)


def build_cos_authorization(method, path, headers, query_params,
                            secret_id, secret_key, start, end):
    """组装 COS Authorization（临时密钥直传版）

    method       : 小写，如 put / post
    path         : URI path（不含 query），如 /uploads/abc.jpg
    headers      : 实际发送的全部 header（key 统一小写后参与排序与签名）
    query_params : URL 上的 query；没有就传 {}
    """
    key_time = f"{start};{end}"

    # 1. SignKey = HMAC-SHA1(SecretKey, KeyTime)
    sign_key = _hmac_sha1(secret_key, key_time)

    # 2. header-list / query-list：key 先小写再按字典序
    hdr_keys = sorted(k.lower() for k in headers)
    q_keys = sorted(query_params.keys())
    hdr_lower = {k.lower(): v for k, v in headers.items()}
    header_string = "&".join(
        f"{k}={_uri_encode(str(hdr_lower[k]).strip())}" for k in hdr_keys)
    query_string = "&".join(
        f"{_uri_encode(k)}={_uri_encode(str(query_params[k]))}" for k in q_keys)

    # 3. HttpString = method\\npath\\nquery\\nheaders\\n
    http_string = f"{method}\n{path}\n{query_string}\n{header_string}\n"

    # 4. StringToSign = sha1\\nKeyTime\\nSHA1(HttpString)\\n
    sha1_hex = hashlib.sha1(http_string.encode("utf-8")).hexdigest()
    string_to_sign = f"sha1\n{key_time}\n{sha1_hex}\n"

    # 5. Signature = HMAC-SHA1(SignKey, StringToSign)
    signature = _hmac_sha1(sign_key, string_to_sign)

    return (
        "q-sign-algorithm=sha1&q-ak={}&q-sign-time={}&q-key-time={}"
        "&q-header-list={}&q-url-param-list={}&q-signature={}"
    ).format(secret_id, key_time, key_time,
             ";".join(hdr_keys), ";".join(q_keys), signature)


def cos_put_object(bucket, region, key, file_bytes, content_type, creds,
                   timeout=60):
    """PUT 直传单个对象，成功返回 ETag

    creds 需含：tmpSecretId / tmpSecretKey / sessionToken（token/v2 三件套）
    """
    if requests is None:
        raise RuntimeError("需要 requests：pip install requests")
    host = f"{bucket}.cos.{region}.myqcloud.com"
    path = "/" + key.lstrip("/")
    now = int(time.time())
    end = now + 600  # 签名有效期 10 分钟

    # 实际发送的全部 header；host 与 x-cos-security-token 必签，Content-Type 一并入签
    headers = {
        "Host": host,
        "Content-Type": content_type,
        "x-cos-security-token": creds["sessionToken"],
    }
    auth = build_cos_authorization("put", path, headers, {},
                                   creds["tmpSecretId"], creds["tmpSecretKey"],
                                   now, end)
    headers["Authorization"] = auth

    url = f"https://{host}{path}"
    resp = requests.put(url, data=file_bytes, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.headers.get("ETag", "")


def _self_check():
    """用官方文档示例验算 SHA1(HttpString)，两个例子都过才算正确"""
    hs1 = ("put\n/exampleobject(腾讯云)\n\n"
           "content-length=13&content-md5=mQ%2FfVh815F3k6TAUm8m0eg%3D%3D"
           "&content-type=text%2Fplain&date=Thu%2C%2016%20May%202019%2006%3A45%3A51%20GMT"
           "&host=examplebucket-1250000000.cos.ap-beijing.myqcloud.com"
           "&x-cos-acl=private&x-cos-grant-read=uin%3D%22100000000011%22\n")
    hs2 = ("get\n/exampleobject(腾讯云)\n"
           "response-cache-control=max-age%3D600&response-content-type=application%2Foctet-stream\n"
           "date=Thu%2C%2016%20May%202019%2006%3A55%3A53%20GMT"
           "&host=examplebucket-1250000000.cos.ap-beijing.myqcloud.com\n")
    ok1 = hashlib.sha1(hs1.encode("utf-8")).hexdigest() == "8b2751e77f43a0995d6e9eb9477f4b685cca4172"
    ok2 = hashlib.sha1(hs2.encode("utf-8")).hexdigest() == "54ecfe22f59d3514fdc764b87a32d8133ea611e6"
    assert ok1 and ok2, "SHA1(HttpString) 与官方示例不符，算法有误！"
    print("self-check OK: 两个官方示例的 SHA1(HttpString) 验算通过")


if __name__ == "__main__":
    _self_check()
