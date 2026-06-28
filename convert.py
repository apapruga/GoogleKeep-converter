from __future__ import annotations

import argparse
import base64
import glob
import hashlib
import html
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser


def format_timestamp(usec):
    """Микросекунды (UTC) -> 'YYYYMMDDTHHMMSSZ'. Пустой/0 -> текущее время UTC."""
    if not usec:
        usec = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    dt = datetime.fromtimestamp(usec / 1_000_000, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def main(argv=None):
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
