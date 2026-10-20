"""MiniMart settings, read from environment variables and a local .env file.

Importing this file does nothing. Call load_settings() to read and check the
settings (the app does this inside create_app()).

Real values live in .env (never committed). .env.example lists the names only.
Real environment variables take priority over .env, which is how a server
should provide them.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

MIN_SECRET_LENGTH = 32

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _fail(message):
    # SystemExit with a string prints just that message and stops the app,
    # so the reason is not buried in a long error trace.
    raise SystemExit(f"MiniMart cannot start: {message}")


def _path(name, default):
    raw = os.environ.get(name, "").strip() or default
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


def _checked_secret_key(value):
    if not value:
        _fail(
            "the setting SECRET_KEY is missing. "
            "Copy .env.example to .env and fill in a real value."
        )
    if len(value) < MIN_SECRET_LENGTH:
        _fail(
            f"SECRET_KEY is too short ({len(value)} characters, "
            f"need at least {MIN_SECRET_LENGTH}). Generate one with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    return value


def _checked_log_level(value):
    level = str(value or "").strip().upper() or "INFO"
    if level not in LOG_LEVELS:
        _fail(f"LOG_LEVEL is {value!r}, but it must be one of: {', '.join(LOG_LEVELS)}.")
    return level


def database_path():
    """Where the database file is. The helper scripts use this: they need no secret key."""
    load_dotenv(BASE_DIR / ".env")
    return _path("DATABASE_PATH", "minimart.db")


def load_settings(overrides=None):
    """Return the app's settings as a dictionary, or stop with a clear message.

    With no overrides, values come from the environment and the .env file.
    Tests pass overrides instead: then neither the environment nor .env is read,
    so a test can never pick up your real key, database or log file.
    Overrides must include SECRET_KEY and DATABASE. LOG_FILE (default: none),
    LOG_LEVEL (default: INFO) and DEBUG (default: False) are optional.
    """
    if overrides is None:
        load_dotenv(BASE_DIR / ".env")
        secret_key = os.environ.get("SECRET_KEY", "").strip()
        database = _path("DATABASE_PATH", "minimart.db")
        log_file = _path("LOG_FILE", "logs/minimart.log")
        log_level = os.environ.get("LOG_LEVEL", "")
        # Debug mode is off unless FLASK_DEBUG is explicitly 1, true or yes.
        debug = os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes")
    else:
        secret_key = str(overrides.get("SECRET_KEY", "")).strip()
        database = overrides.get("DATABASE")
        if not database:
            _fail("the test settings must include DATABASE, a path to a throwaway database file.")
        log_file = overrides.get("LOG_FILE")
        log_level = overrides.get("LOG_LEVEL", "")
        debug = bool(overrides.get("DEBUG", False))

    return {
        "SECRET_KEY": _checked_secret_key(secret_key),
        "DATABASE": str(database),
        "LOG_FILE": log_file,
        "LOG_LEVEL": _checked_log_level(log_level),
        "DEBUG": debug,
    }
