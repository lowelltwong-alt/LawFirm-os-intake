from __future__ import annotations

import json
from hashlib import sha256
from typing import Any


def calibration_release_digest(payload: dict[str, Any]) -> str:
    """Bind synthetic release evidence without serializing replay-seed material."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{sha256(encoded.encode('utf-8')).hexdigest()}"
