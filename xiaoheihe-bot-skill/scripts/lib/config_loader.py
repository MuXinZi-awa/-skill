from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    raw = config_path.read_bytes()
    config: dict[str, Any] | None = None
    last_error: Exception | None = None

    for enc in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            config = json.loads(raw.decode(enc))
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    if config is None:
        raise ValueError(f"Failed to parse config JSON: {config_path}; last_error={last_error}")

    required = ["request", "auth", "policy", "log"]
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing required config sections: {', '.join(missing)}")

    return config
