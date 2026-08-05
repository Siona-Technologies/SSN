"""
In-process asynchronous cognitive event bus.

Features:
- publish / subscribe with event-type filtering
- priority-aware dequeue
- bounded queues + backpressure (drop or reject)
- handler timeouts and failure isolation
- optional dead-letter recording
- metrics counters
- graceful shutdown

No external broker. A transport adapter can wrap publish/subscribe later.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
)

from ssn.cognition.events import CognitiveEvent, EventPriority

logger = logging.getLogger(__name__)

EventHandler = Callable[[CognitiveEvent], Union[None, Awaitable[None]]]
EventFilter = Union[str, Sequence[str], Pattern[str], Callable[[CognitiveEvent], bool], None]


@dataclass
class EventBusMetrics:
    published: int = 0
    delivered: int = 0
    dropped: int = 0
    rejected: int = 0
    handler_errors: int = 0
    handler_timeouts: int = 0
    dead_letters: int = 0
    max_queue_depth: int = 0
    last_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    latency_samples: int = 0

    def record_latency(self, latency_ms: float) -> None:
        self.last_latency_ms = float(latency_ms)
        self.total_latency_ms += float(latency_ms)
        self.latency_samples += 1

    @property
    def avg_latency_ms(self) -> float:
        if self.latency_samples <= 0:
            return 0.0
        return self.total_latency_ms / self.latency_samples

    def snapshot(self) -> Dict[str, Any]:
        return {
            "published": self.published,
            "delivered": self.delivered,
            "dropped": self.dropped,
            "rejected": self.rejected,
            "handler_errors": self.handler_errors,
            "handler_timeouts": self.handler_timeouts,
            "dead_letters": self.dead_letters,
            "max_queue_depth": self.max_queue_depth,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "latency_samples": self.latency_samples,
        }


@dataclass
class DeadLetter:
    event: CognitiveEvent
    reason: str
    timestamp: float = field(default_factory=time.time)
    error: str = ""


@dataclass
class _Subscription:
    handler: EventHandler
    event_filter: EventFilter = None
    name: str = ""

    def matches(self, event: CognitiveEvent) -> bool:
        f = self.event_filter
        if f is None:
            return True
        if isinstance(f, str):
            return event.event_type == f or event.event_type.startswith(f.rstrip("*"))
        if isinstance(f, (list, tuple, set)):
            return event.event_type in f
        if hasattr(f, "search"):  # compiled regex
            try:
                return bool(f.search(event.event_type))  # type: ignore[union-attr]
            except Exception:
                return False
        if callable(f):
            try:
                return bool(f(event))
            except Exception:
                return False
        return False


class AsyncEventBus:
    """
    Priority asyncio event bus for local cognitive runtime use.
    """

    def __init__(
        self,
        *,
        max_queue_size: int = 1024,
        handler_timeout_s: float = 2.0,
        drop_on_full: bool = True,
        dead_letter_capacity: int = 128,
        name: str = "siona-event-bus",
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be >= 1")
        self.name = name
        self.max_queue_size = int(max_queue_size)
        self.handler_timeout_s = float(handler_timeout_s)
        self.drop_on_full = bool(drop_on_full)
        self.dead_letter_capacity = int(dead_letter_capacity)

        self._queues: Dict[EventPriority, Deque[CognitiveEvent]] = {
            p: deque() for p in EventPriority
        }
        self._subs: List[_Subscription] = []
        self._metrics = EventBusMetrics()
        self._dead_letters: Deque[DeadLetter] = deque(maxlen=self.dead_letter_capacity)
        self._cond: Optional[asyncio.Condition] = None
        self._worker: Optional[asyncio.Task[None]] = None
        self._running = False
        self._closed = False
        self._depth = 0

    @property
    def metrics(self) -> EventBusMetrics:
        return self._metrics

    @property
    def queue_depth(self) -> int:
        return self._depth

    @property
    def is_running(self) -> bool:
        return self._running and not self._closed

    def dead_letters(self) -> List[DeadLetter]:
        return list(self._dead_letters)

    def subscribe(
        self,
        handler: EventHandler,
        *,
        event_type: EventFilter = None,
        name: str = "",
    ) -> Callable[[], None]:
        """
        Register a handler. Returns an unsubscribe callable.
        Filtering: exact type, prefix with trailing '*', list, regex, or predicate.
        """
        sub = _Subscription(handler=handler, event_filter=event_type, name=name or getattr(handler, "__name__", ""))
        self._subs.append(sub)

        def _unsub() -> None:
            try:
                self._subs.remove(sub)
            except ValueError:
                pass

        return _unsub

    async def start(self) -> None:
        if self._closed:
            raise RuntimeError("event bus is closed")
        if self._running:
            return
        self._cond = asyncio.Condition()
        self._running = True
        self._worker = asyncio.create_task(self._run_loop(), name=f"{self.name}-worker")

    async def stop(self, *, drain: bool = True, timeout_s: float = 5.0) -> None:
        if not self._running:
            self._closed = True
            return
        self._running = False
        if self._cond is not None:
            async with self._cond:
                self._cond.notify_all()
        if self._worker is not None:
            try:
                if drain:
                    await asyncio.wait_for(self._worker, timeout=timeout_s)
                else:
                    self._worker.cancel()
                    try:
                        await self._worker
                    except asyncio.CancelledError:
                        pass
            except asyncio.TimeoutError:
                self._worker.cancel()
                try:
                    await self._worker
                except asyncio.CancelledError:
                    pass
            self._worker = None
        self._closed = True

    async def publish(self, event: CognitiveEvent) -> bool:
        """
        Enqueue an event. Returns False if rejected/dropped under backpressure.
        """
        if self._closed:
            self._metrics.rejected += 1
            return False
        if not isinstance(event, CognitiveEvent):
            raise TypeError("publish expects CognitiveEvent")
        if event.is_expired():
            self._record_dead_letter(event, "expired_before_publish")
            self._metrics.rejected += 1
            return False

        if self._cond is None:
            # Lazy start support for sync-friendly tests that only call publish after start.
            self._cond = asyncio.Condition()

        async with self._cond:
            if self._depth >= self.max_queue_size:
                if self.drop_on_full:
                    dropped = self._drop_lowest_priority_locked()
                    if dropped is not None:
                        self._metrics.dropped += 1
                        self._record_dead_letter(dropped, "backpressure_drop")
                    else:
                        self._metrics.rejected += 1
                        return False
                else:
                    self._metrics.rejected += 1
                    return False

            self._queues[event.priority].append(event)
            self._depth += 1
            self._metrics.published += 1
            if self._depth > self._metrics.max_queue_depth:
                self._metrics.max_queue_depth = self._depth
            self._cond.notify()
            return True

    def publish_nowait(self, event: CognitiveEvent) -> bool:
        """
        Synchronous enqueue helper for sync contexts.
        Caller must ensure an event loop is running if workers are active.
        """
        if self._closed:
            self._metrics.rejected += 1
            return False
        if event.is_expired():
            self._record_dead_letter(event, "expired_before_publish")
            self._metrics.rejected += 1
            return False
        if self._depth >= self.max_queue_size:
            if self.drop_on_full:
                dropped = self._drop_lowest_priority_locked()
                if dropped is not None:
                    self._metrics.dropped += 1
                    self._record_dead_letter(dropped, "backpressure_drop")
                else:
                    self._metrics.rejected += 1
                    return False
            else:
                self._metrics.rejected += 1
                return False
        self._queues[event.priority].append(event)
        self._depth += 1
        self._metrics.published += 1
        if self._depth > self._metrics.max_queue_depth:
            self._metrics.max_queue_depth = self._depth
        return True

    async def publish_and_dispatch(self, event: CognitiveEvent) -> None:
        """Publish then immediately dispatch to matching handlers (no worker required)."""
        ok = await self.publish(event)
        if not ok:
            return
        # Pull the just-published event if still at head of its priority queue.
        popped = self._pop_event_by_id(event.event_id)
        if popped is None:
            return
        await self._dispatch(popped)

    def _pop_event_by_id(self, event_id: str) -> Optional[CognitiveEvent]:
        for priority in sorted(EventPriority, reverse=True):
            q = self._queues[priority]
            for i, ev in enumerate(q):
                if ev.event_id == event_id:
                    del q[i]
                    self._depth = max(0, self._depth - 1)
                    return ev
        return None

    def _drop_lowest_priority_locked(self) -> Optional[CognitiveEvent]:
        for priority in sorted(EventPriority):
            q = self._queues[priority]
            if q:
                ev = q.popleft()
                self._depth = max(0, self._depth - 1)
                return ev
        return None

    def _pop_highest_priority(self) -> Optional[CognitiveEvent]:
        for priority in sorted(EventPriority, reverse=True):
            q = self._queues[priority]
            if q:
                self._depth = max(0, self._depth - 1)
                return q.popleft()
        return None

    async def _run_loop(self) -> None:
        assert self._cond is not None
        while self._running or self._depth > 0:
            async with self._cond:
                while self._depth == 0 and self._running:
                    await self._cond.wait()
                if self._depth == 0 and not self._running:
                    return
                event = self._pop_highest_priority()
            if event is None:
                continue
            await self._dispatch(event)

    async def _dispatch(self, event: CognitiveEvent) -> None:
        if event.is_expired():
            self._record_dead_letter(event, "expired_before_dispatch")
            self._metrics.rejected += 1
            return

        start = time.monotonic()
        matched = 0
        for sub in list(self._subs):
            if not sub.matches(event):
                continue
            matched += 1
            try:
                result = sub.handler(event)
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    await asyncio.wait_for(result, timeout=self.handler_timeout_s)
            except asyncio.TimeoutError:
                self._metrics.handler_timeouts += 1
                self._record_dead_letter(event, f"handler_timeout:{sub.name}")
                logger.warning(
                    "event handler timeout bus=%s handler=%s type=%s",
                    self.name,
                    sub.name,
                    event.event_type,
                )
            except Exception as exc:
                self._metrics.handler_errors += 1
                self._record_dead_letter(event, f"handler_error:{sub.name}", error=str(exc))
                logger.warning(
                    "event handler error bus=%s handler=%s type=%s err=%s",
                    self.name,
                    sub.name,
                    event.event_type,
                    exc,
                )

        latency_ms = (time.monotonic() - start) * 1000.0
        self._metrics.record_latency(latency_ms)
        if matched > 0:
            self._metrics.delivered += 1
        else:
            # No subscribers — keep as informational dead-letter only if attention required.
            if event.requires_attention:
                self._record_dead_letter(event, "no_subscribers")

    def _record_dead_letter(
        self,
        event: CognitiveEvent,
        reason: str,
        *,
        error: str = "",
    ) -> None:
        self._dead_letters.append(DeadLetter(event=event, reason=reason, error=error))
        self._metrics.dead_letters += 1

    async def drain(self, *, timeout_s: float = 2.0) -> None:
        """Wait until queue is empty or timeout."""
        deadline = time.monotonic() + timeout_s
        while self._depth > 0 and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
