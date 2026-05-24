from __future__ import annotations

import os
from pathlib import Path


def resolve_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    env_file = Path(".env")
    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip().upper() == "DATABASE_URL":
                parsed = value.strip().strip('"').strip("'")
                if parsed:
                    return parsed

    raise RuntimeError("DATABASE_URL is required (env var or .env at project root)")
