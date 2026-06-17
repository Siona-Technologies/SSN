# ssn/runtime/tenant_config.py
"""
Tenant isolation helpers for multi-deployment SIONA (Phase 3).

Uses X-SSN-Tenant-ID header or SSN_TENANT_ID env to isolate state directories.
Law paths can be set per-tenant via env files in deploy/<tenant>/.env
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

_TENANT_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")


def normalize_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    if not isinstance(tenant_id, str):
        return None
    tid = tenant_id.strip()
    if not tid or not _TENANT_RE.match(tid):
        return None
    return tid


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: Optional[str]
    state_dir: str
    knowledge_path: Optional[str] = None
    home_law_path: Optional[str] = None
    world_law_path: Optional[str] = None
    system_law_path: Optional[str] = None


def resolve_tenant_id(*, header_value: Optional[str] = None) -> Optional[str]:
    if header_value:
        tid = normalize_tenant_id(header_value)
        if tid:
            return tid
    env_tid = os.getenv("SSN_TENANT_ID")
    return normalize_tenant_id(env_tid)


def tenant_state_dir(base_state_dir: str, tenant_id: Optional[str]) -> str:
    base = base_state_dir or ".ssn_state"
    tid = normalize_tenant_id(tenant_id)
    if not tid:
        return base
    return os.path.join(base, "tenants", tid)


def load_tenant_config(*, tenant_id: Optional[str] = None, base_state_dir: Optional[str] = None) -> TenantConfig:
    tid = normalize_tenant_id(tenant_id)
    base = base_state_dir or os.getenv("SSN_STATE_DIR") or ".ssn_state"
    state_dir = tenant_state_dir(base, tid)

    prefix = f"SSN_TENANT_{tid.upper().replace('-', '_').replace('.', '_')}_" if tid else ""

    def _tenant_env(suffix: str, fallback_env: str) -> Optional[str]:
        if tid and prefix:
            v = os.getenv(f"{prefix}{suffix}")
            if isinstance(v, str) and v.strip():
                return v.strip()
        v2 = os.getenv(fallback_env)
        return v2.strip() if isinstance(v2, str) and v2.strip() else None

    return TenantConfig(
        tenant_id=tid,
        state_dir=state_dir,
        knowledge_path=_tenant_env("KNOWLEDGE_PATH", "SSN_KNOWLEDGE_PATH"),
        home_law_path=_tenant_env("HOME_LAW_PATH", "SSN_HOME_LAW_PATH"),
        world_law_path=_tenant_env("WORLD_LAW_PATH", "SSN_WORLD_LAW_PATH"),
        system_law_path=_tenant_env("SYSTEM_LAW_PATH", "SSN_SYSTEM_LAW_PATH"),
    )
