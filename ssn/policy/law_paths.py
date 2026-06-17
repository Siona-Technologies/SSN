# ssn/policy/law_paths.py
"""
Resolve policy law file paths from environment or defaults.
"""

from __future__ import annotations

import os
from typing import Optional

_DEFAULT_DIR = os.path.dirname(__file__)


def _resolve(path: Optional[str], default_filename: str) -> str:
    if isinstance(path, str) and path.strip():
        p = path.strip()
        if os.path.isabs(p):
            return p
        return os.path.abspath(p)
    return os.path.join(_DEFAULT_DIR, default_filename)


def world_law_path(explicit: Optional[str] = None) -> str:
    return _resolve(explicit or os.getenv("SSN_WORLD_LAW_PATH"), "world_law.yaml")


def system_law_path(explicit: Optional[str] = None) -> str:
    return _resolve(explicit or os.getenv("SSN_SYSTEM_LAW_PATH"), "system_law.yaml")


def home_law_path(explicit: Optional[str] = None) -> str:
    return _resolve(explicit or os.getenv("SSN_HOME_LAW_PATH"), "home_law_samson.yaml")
