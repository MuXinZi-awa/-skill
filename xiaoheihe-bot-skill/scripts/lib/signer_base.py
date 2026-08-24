from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignKeys:
    hkey: str
    nonce: str
    Rtime: int


class Signer:
    def get_keys(self, req_path: str) -> SignKeys:
        raise NotImplementedError
