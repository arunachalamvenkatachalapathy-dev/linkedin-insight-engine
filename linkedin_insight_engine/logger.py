from __future__ import annotations

import json
import logging
import sys
from typing import Any


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )


def log_event(stage: str, status: str, **fields: Any) -> None:
    payload = {"stage": stage, "status": status, **fields}
    logging.info(json.dumps(payload, sort_keys=True))
