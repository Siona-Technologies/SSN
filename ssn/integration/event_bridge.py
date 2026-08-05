"""
Core event publication helper for integration bridges.

Async safety:
- emit_async is preferred in async contexts.
- emit_sync uses asyncio.run when no loop is running.
- When a loop is already running, emission is tracked in a bounded pending-task
  registry (not fire-and-forget). Call drain()/shutdown() on teardown.
- shutdown_sync() raises if called inside a running event loop — use await shutdown().
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Set

from ssn.cognition.event_bus import AsyncEventBus
from ssn.cognition.events import CognitiveEvent, EventPriority
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext

logger = logging.getLogger(__name__)


class EventBridgeSyncInAsyncContextError(RuntimeError):
    """Raised when emit_sync cannot safely schedule work (registry full)."""


class EventBridgeShutdownInAsyncContextError(RuntimeError):
    """Raised when shutdown_sync is called inside a running event loop."""


class EventBridge:
    """Publish redacted cognitive events onto the shared in-process bus."""

    DEFAULT_MAX_PENDING = 256

    def __init__(
        self,
        bus: AsyncEventBus,
        *,
        metrics: Any = None,
        max_pending_tasks: int = DEFAULT_MAX_PENDING,
    ) -> None:
        self.bus = bus
        self.metrics = metrics
        self.max_pending_tasks = int(max_pending_tasks)
        self._publish_errors = 0
        self._pending: Set[asyncio.Task[Any]] = set()
        self._closed = False

    @property
    def pending_task_count(self) -> int:
        self._pending = {t for t in self._pending if not t.done()}
        return len(self._pending)

    def _build_event(
        self,
        event_type: str,
        *,
        source: str,
        payload: Optional[Dict[str, Any]],
        trace: Optional[TraceContext],
        priority: EventPriority,
        requires_attention: bool,
        confidence: float,
    ) -> CognitiveEvent:
        tr = trace or TraceContext()
        return CognitiveEvent(
            event_type=event_type,
            source=source,
            payload=redact(dict(payload or {})),
            priority=priority,
            confidence=confidence,
            trace_id=tr.trace_id,
            correlation_id=tr.correlation_id,
            tenant_id=tr.tenant_id,
            session_id=tr.session_id,
            requires_attention=requires_attention,
            metadata={
                "runtime_mode": tr.runtime_mode,
                "role": tr.role,
            },
        )

    def _record_success(self, event_type: str) -> None:
        if self.metrics is not None:
            self.metrics.inc_event(event_type)

    def _record_error(self, event_type: str, exc: BaseException) -> None:
        self._publish_errors += 1
        if self.metrics is not None:
            self.metrics.event_delivery_errors += 1
        logger.warning("event bridge emit failed type=%s err=%s", event_type, exc)

    def _on_task_done(self, task: asyncio.Task[Any], event_type: str) -> None:
        self._pending.discard(task)
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        except Exception as exc:
            self._record_error(event_type, exc)
            return
        if exc is not None:
            self._record_error(event_type, exc)
        else:
            self._record_success(event_type)

    def _schedule_tracked(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
        event_type: str,
    ) -> asyncio.Task[Any]:
        """
        Admit then construct the coroutine — avoids unawaited-coroutine leaks
        when the pending registry is full.
        """
        if self._closed:
            raise RuntimeError("event bridge is shut down")
        if self.pending_task_count >= self.max_pending_tasks:
            raise EventBridgeSyncInAsyncContextError(
                f"pending observation task registry full ({self.max_pending_tasks}); "
                "await EventBridge.drain() or use emit_async with backpressure"
            )
        coro = coro_factory()
        task = asyncio.create_task(coro, name=f"siona-obs-{event_type}")
        self._pending.add(task)
        task.add_done_callback(lambda t: self._on_task_done(t, event_type))
        return task

    def emit_sync(
        self,
        event_type: str,
        *,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        trace: Optional[TraceContext] = None,
        priority: EventPriority = EventPriority.NORMAL,
        requires_attention: bool = False,
        confidence: float = 1.0,
    ) -> Optional[CognitiveEvent]:
        """
        Sync emit for non-async call sites (CLI / Front Door).

        When an event loop is already running, schedules a *tracked* task
        (bounded registry). Prefer emit_async in async code paths.
        """
        if self._closed:
            self._record_error(event_type, RuntimeError("bridge_closed"))
            return None

        event = self._build_event(
            event_type,
            source=source,
            payload=payload,
            trace=trace,
            priority=priority,
            requires_attention=requires_attention,
            confidence=confidence,
        )
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                self._schedule_tracked(
                    lambda: self.bus.dispatch_inline(event),
                    event_type,
                )
                return event

            asyncio.run(self.bus.dispatch_inline(event))
            self._record_success(event_type)
            return event
        except Exception as exc:
            self._record_error(event_type, exc)
            return None

    async def emit_async(
        self,
        event_type: str,
        *,
        source: str,
        payload: Optional[Dict[str, Any]] = None,
        trace: Optional[TraceContext] = None,
        priority: EventPriority = EventPriority.NORMAL,
        requires_attention: bool = False,
        confidence: float = 1.0,
    ) -> Optional[CognitiveEvent]:
        if self._closed:
            self._record_error(event_type, RuntimeError("bridge_closed"))
            return None
        event = self._build_event(
            event_type,
            source=source,
            payload=payload,
            trace=trace,
            priority=priority,
            requires_attention=requires_attention,
            confidence=confidence,
        )
        try:
            await self.bus.dispatch_inline(event)
            self._record_success(event_type)
            return event
        except Exception as exc:
            self._record_error(event_type, exc)
            return None

    async def drain(self, *, timeout_s: float = 5.0) -> None:
        """Await pending observation tasks (or cancel on timeout). Never waits on self."""
        try:
            current = asyncio.current_task()
        except RuntimeError:
            current = None
        pending = [
            t
            for t in list(self._pending)
            if not t.done() and t is not current
        ]
        if not pending:
            self._pending = {t for t in self._pending if not t.done()}
            return
        _done, still = await asyncio.wait(pending, timeout=timeout_s)
        for t in still:
            t.cancel()
        if still:
            await asyncio.gather(*still, return_exceptions=True)
        self._pending = {t for t in self._pending if not t.done()}

    async def shutdown(self, *, timeout_s: float = 5.0) -> None:
        """Drain then mark closed — no further emissions."""
        await self.drain(timeout_s=timeout_s)
        self._closed = True

    def shutdown_sync(self, *, timeout_s: float = 5.0) -> None:
        """
        Sync wrapper for callers without a running event loop.

        Raises if invoked inside a running loop — use ``await shutdown()`` instead.
        Never schedules shutdown through the pending-task registry.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None and loop.is_running():
            raise EventBridgeShutdownInAsyncContextError(
                "shutdown_sync() cannot be called inside a running event loop; "
                "use await EventBridge.shutdown() / await runtime.shutdown()"
            )
        asyncio.run(self.shutdown(timeout_s=timeout_s))
