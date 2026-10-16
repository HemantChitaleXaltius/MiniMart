"""MiniMart settings, read from environment variables and a local .env file.

Real values live in .env (never committed). .env.example lists the names only.
Real environment variables take priority over .env, which is how a server
should provide them.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MIN_SECRET_LENGTH = 32


def _fail(message):
    # SystemExit with a string prints just that message and stops the app,
    # so the reason is not buried in a long error trace.
    raise SystemExit(f"MiniMart cannot start: {message}")


def _required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        _fail(
            f"the setting {name} is missing. "
            "Copy .env.example to .env and fill in a real value."
        )
    return value


def _path(name, default):
    raw = os.environ.get(name, "").strip() or default
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


SECRET_KEY = _required("SECRET_KEY")
if len(SECRET_KEY) < MIN_SECRET_LENGTH:
    _fail(
        f"SECRET_KEY is too short ({len(SECRET_KEY)} characters, "
        f"need at least {MIN_SECRET_LENGTH}). Generate one with: "
        'python -c "import secrets; print(secrets.token_hex(32))"'
    )

DATABASE_PATH = _path("DATABASE_PATH", "minimart.db")
LOG_FILE = _path("LOG_FILE", "minimart.log")

# Debug mode is off unless FLASK_DEBUG is explicitly 1, true or yes.
DEBUG = os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes")
