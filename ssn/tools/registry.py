# ssn/tools/registry.py

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from ssn.tools.contracts import ToolResult, ToolSpec


class _FileRateLimiter:
    """
    File-backed fixed-window rate limiter.

    Key:
      (tool_name, role, minute_bucket) -> count

    Notes:
    - Fixed window is good enough for Phase 7.x and easy to reason about.
    - Stored in a JSON file so separate CLI invocations still share limits.
    - Best-effort atomic writes (os.replace). Concurrency safety is "good enough"
      for local dev; if you later run multi-worker servers, add a real lock.
    """

    def __init__(self, path: str) -> None:
        self.path = path

    def _load(self) -> Dict[str, int]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: Dict[str, int]) -> None:
        """
        Best-effort atomic save. If it fails, caller may choose to fail-open.
        """
        tmp = f"{self.path}.tmp"
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        except Exception:
            # directory create failed; still attempt write in case path has no dir component
            pass

        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    @staticmethod
    def _minute_bucket(ts: float) -> int:
        return int(ts // 60)

    @staticmethod
    def _key(tool: str, role: str, bucket: int) -> str:
        return f"{tool}::{role}::{bucket}"

    def check_and_increment(
        self,
        *,
        tool: str,
        role: str,
        limit_per_minute: int,
        now_ts: Optional[float] = None,
    ) -> Tuple[bool, int, int]:
        """
        Returns (allowed, used_in_window, retry_after_seconds)
        """
        if limit_per_minute <= 0:
            return True, 0, 0

        now = float(now_ts if now_ts is not None else time.time())
        bucket = self._minute_bucket(now)
        k = self._key(tool, role, bucket)

        db = self._load()

        # prune: keep only recent buckets to prevent growth
        # keep last 3 minutes for all tools/roles
        min_keep = bucket - 2
        pruned: Dict[str, int] = {}
        for kk, vv in db.items():
            if not isinstance(kk, str):
                continue
            if not isinstance(vv, int):
                continue
            try:
                b = int(kk.split("::")[-1])
            except Exception:
                continue
            if b >= min_keep:
                pruned[kk] = vv

        used = int(pruned.get(k, 0))
        if used >= limit_per_minute:
            # retry at next minute boundary
            next_bucket_start = (bucket + 1) * 60
            retry_after = max(1, int(next_bucket_start - now))
            return False, used, retry_after

        pruned[k] = used + 1

        try:
            self._save(pruned)
        except Exception:
            # If saving fails, fail open (don’t brick tools due to filesystem issues)
            return True, used + 1, 0

        return True, used + 1, 0


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

        # Default location for rate limit state:
        # - override with env var SSN_RATE_LIMIT_PATH if you want
        # - otherwise persists across CLI invocations in the same machine/container
        path = os.environ.get("SSN_RATE_LIMIT_PATH")
        if not isinstance(path, str) or not path.strip():
            path = "/tmp/ssn_rate_limit.json"
        self._rate_limiter = _FileRateLimiter(path.strip())

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or not isinstance(spec.name, str):
            raise ValueError("Tool name must be a non-empty string.")
        self._tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    # -----------------------------
    # Listing
    # -----------------------------
    def _spec_to_dict(self, spec: ToolSpec) -> Dict[str, Any]:
        roles_allowed = None
        try:
            roles_allowed = list(spec.roles_allowed())  # type: ignore[attr-defined]
        except Exception:
            roles_allowed = None

        public = bool(getattr(spec, "public", False))
        max_cpm = getattr(spec, "max_calls_per_minute", None)

        return {
            "description": spec.description,
            "required_role": getattr(spec, "required_role", "OWNER"),
            "allowed_roles": roles_allowed,
            "public": public,
            "state_changing": bool(getattr(spec, "state_changing", False)),
            "max_calls_per_minute": max_cpm,
            "input_schema": dict(getattr(spec, "input_schema", {}) or {}),
        }

    def list(self) -> Dict[str, Dict[str, Any]]:
        """List all tools (admin/OWNER introspection)."""
        return {
            name: self._spec_to_dict(spec)
            for name, spec in sorted(self._tools.items(), key=lambda kv: kv[0])
        }

    def list_public(self, *, role: str = "GUEST") -> Dict[str, Dict[str, Any]]:
        """
        List only tools that are marked public AND allowed for the given role.
        Intended for guest-safe discovery.
        """
        out: Dict[str, Dict[str, Any]] = {}
        for name, spec in sorted(self._tools.items(), key=lambda kv: kv[0]):
            if not bool(getattr(spec, "public", False)):
                continue
            if not self._is_role_allowed(spec, role):
                continue
            out[name] = self._spec_to_dict(spec)
        return out

    # -----------------------------
    # Permission checks
    # -----------------------------
    @staticmethod
    def _is_role_allowed(spec: ToolSpec, role: str) -> bool:
        fn = getattr(spec, "is_role_allowed", None)
        if callable(fn):
            try:
                return bool(fn(role))  # type: ignore[misc]
            except Exception:
                pass

        required = getattr(spec, "required_role", "OWNER")
        if required == "OWNER" and role != "OWNER":
            return False
        return True

    @staticmethod
    def _is_state_change_allowed(spec: ToolSpec, role: str) -> bool:
        if bool(getattr(spec, "state_changing", False)) and role != "OWNER":
            return False
        return True

    def _rate_limit_allowed(self, *, spec: ToolSpec, tool_name: str, role: str) -> Optional[Dict[str, Any]]:
        """
        Returns None if allowed, else an error dict.
        """
        max_cpm = getattr(spec, "max_calls_per_minute", None)
        if max_cpm is None:
            return None
        try:
            limit = int(max_cpm)
        except Exception:
            return None
        if limit <= 0:
            return None

        allowed, used, retry_after = self._rate_limiter.check_and_increment(
            tool=tool_name,
            role=role,
            limit_per_minute=limit,
        )
        if allowed:
            return None

        return {
            "code": "RATE_LIMITED",
            "message": f"Rate limit exceeded for tool '{tool_name}' (role={role}). limit={limit}/min used={used}.",
            "retry_after_s": retry_after,
            "limit_per_minute": limit,
            "used_in_current_window": used,
        }

    # -----------------------------
    # Execution
    # -----------------------------
    def run(self, *, name: str, role: str, deps: Dict[str, Any], args: Dict[str, Any]) -> ToolResult:
        spec = self.get(name)
        if spec is None:
            return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_NOT_FOUND", "message": name})

        if not self._is_role_allowed(spec, role):
            return ToolResult(
                ok=False,
                tool=name,
                role=role,
                error={"code": "TOOL_FORBIDDEN", "message": f"Role '{role}' not allowed for tool '{name}'"},
            )

        if not self._is_state_change_allowed(spec, role):
            return ToolResult(
                ok=False,
                tool=name,
                role=role,
                error={"code": "TOOL_STATE_CHANGE_FORBIDDEN", "message": "State-changing tools require OWNER"},
            )

        # Rate limit (applies after permission checks)
        rl_err = self._rate_limit_allowed(spec=spec, tool_name=name, role=role)
        if rl_err is not None:
            return ToolResult(ok=False, tool=name, role=role, error=rl_err)

        try:
            out = spec.handler(deps, args or {})
            if not isinstance(out, dict):
                out = {"result": out}
            return ToolResult(ok=True, tool=name, role=role, data=out)
        except Exception as e:
            return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_ERROR", "message": str(e)})
