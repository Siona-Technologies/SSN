"""
Core event publication helper for integration bridges.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from ssn.cognition.event_bus import AsyncEventBus
from ssn.cognition.events import CognitiveEvent, EventPriority
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext

logger = logging.getLogger(__name__)


class EventBridge:
    """Publish redacted cognitive events onto the shared in-process bus."""

    def __init__(
        self,
        bus: AsyncEventBus,
        *,
        metrics: Any = None,
    ) -> None:
        self.bus = bus
        self.metrics = metrics
        self._publish_errors = 0

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
        Build and inline-dispatch an event without leaving queue residue.
        Safe for sync call sites (uses a short asyncio.run when no loop).
        """
        tr = trace or TraceContext()
        event = CognitiveEvent(
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
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # Schedule without blocking; fire-and-forget for observation path.
                loop.create_task(self.bus.dispatch_inline(event))
            else:
                asyncio.run(self.bus.dispatch_inline(event))
            if self.metrics is not None:
                self.metrics.inc_event(event_type)
            return event
        except Exception as exc:
            self._publish_errors += 1
            if self.metrics is not None:
                self.metrics.event_delivery_errors += 1
            logger.warning("event bridge emit failed type=%s err=%s", event_type, exc)
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
        tr = trace or TraceContext()
        event = CognitiveEvent(
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
        try:
            await self.bus.dispatch_inline(event)
            if self.metrics is not None:
                self.metrics.inc_event(event_type)
            return event
        except Exception as exc:
            self._publish_errors += 1
            if self.metrics is not None:
                self.metrics.event_delivery_errors += 1
            logger.warning("event bridge emit failed type=%s err=%s", event_type, exc)
            return None
