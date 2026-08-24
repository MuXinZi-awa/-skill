from __future__ import annotations

import hashlib
import secrets
import time

from signer_base import SignKeys, Signer


class CustomSigner(Signer):
    def get_keys(self, req_path: str) -> SignKeys:
        _time = int(time.time())
        nonce = self._get_nonce(_time)
        r = "AB45STUVWZEFGJ6CH01D237IXYPQRKLMN89"

        str1 = self._av(str(_time), r, -2)
        str2 = self._sv(req_path, r)
        str3 = self._sv(nonce, r)

        str_arr = [str1, str2, str3]
        # 按字符串长度从小到大排序
        str_arr.sort(key=len)

        new_string = self._new_str(str_arr)
        # 截取前 20 个字符进行 MD5
        _md5 = hashlib.md5(new_string[:20].encode()).hexdigest()

        lastsix = _md5[-6:]
        # 将最后6位字符转为对应的 ASCII 码值
        lastsix_arr = [ord(v) for v in lastsix]

        mix = self._mixed(lastsix_arr)
        count = sum(mix)

        a = f"{count % 100:02d}"
        s = self._av(_md5[0:5], r, -4)

        hkey = s + a

        # 假设 SignKeys 是一个 dataclass 或 pydantic 模型，根据实际定义调整字段名
        return SignKeys(hkey=hkey, nonce=nonce, Rtime=_time)

    # --- 核心混淆与加密逻辑 (私有方法) ---

    def _get_nonce(self, Time: int) -> str:
        # 使用 secrets 生成加密安全的随机数
        random_val = secrets.randbelow(Time * 1000)
        str_val = str(Time) + str(random_val)
        _md5 = hashlib.md5(str_val.encode()).hexdigest()
        return _md5.upper()

    def _av(self, str_val: str, key: str, n: int) -> str:
        i = key[0:len(key) + n]
        r = []
        for v in str_val:
            p = i[ord(v) % len(i)]
            r.append(p)
        return ''.join(r)

    def _sv(self, str_val: str, key: str) -> str:
        n = []
        for v in str_val:
            p = key[ord(v) % len(key)]
            n.append(p)
        return ''.join(n)

    def _new_str(self, arr: list[str]) -> str:
        str_list = []
        # 以最长的字符串（arr[2]）的长度为基准进行遍历
        for i in range(len(arr[2])):
            if len(arr[0]) > i:
                str_list.append(arr[0][i])
            if len(arr[1]) > i:
                str_list.append(arr[1][i])
            if len(arr[2]) > i:
                str_list.append(arr[2][i])
        return ''.join(str_list)

    def _mixed(self, e: list[int]) -> list[int]:
        t = [0] * 6
        t[0] = self._Gm(e[0]) ^ self._Ym(e[1]) ^ self._m(e[2]) ^ self._qm(e[3])
        t[1] = self._qm(e[0]) ^ self._Gm(e[1]) ^ self._Ym(e[2]) ^ self._m(e[3])
        t[2] = self._m(e[0]) ^ self._qm(e[1]) ^ self._Gm(e[2]) ^ self._Ym(e[3])
        t[3] = self._Ym(e[0]) ^ self._m(e[1]) ^ self._qm(e[2]) ^ self._Gm(e[3])
        t[4] = e[4]
        t[5] = e[5]
        return t

    def _Vm(self, num: int) -> int:
        if num & 128 != 0:
            return ((num << 1) ^ 27) & 255
        return num << 1

    def _qm(self, num: int) -> int:
        return self._Vm(num) ^ num

    def _m(self, num: int) -> int:
        return self._qm(self._Vm(num))

    def _Ym(self, num: int) -> int:
        return self._m(self._qm(self._Vm(num)))

    def _Gm(self, num: int) -> int:
        return self._Ym(num) ^ self._m(num) ^ self._qm(num)