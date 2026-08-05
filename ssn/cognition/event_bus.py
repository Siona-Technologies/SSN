"""
In-process asynchronous cognitive event bus.

Features:
- publish / subscribe with event-type filtering
- priority-aware dequeue and backpressure
- bounded queues
- handler timeouts and failure isolation
- optional dead-letter recording
- metrics counters
- graceful shutdown
- inline dispatch (no queue leak for request/response paths)

Backpressure policy (when full):
  1. Find oldest event at the lowest queued priority (FIFO within that priority).
  2. If incoming priority is strictly higher, evict that queued event and admit.
  3. Otherwise reject the incoming event (never evict equal/higher-value work).

Filter semantics:
  - "sensor.imu"  → exact match only
  - "sensor.*"    → prefix match (startswith "sensor.")
  - list/tuple/set → each element evaluated with the same rules
  - regex / predicate unchanged
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
    Union,
)

from ssn.cognition.events import CognitiveEvent, EventPriority

logger = logging.getLogger(__name__)

EventHandler = Callable[[CognitiveEvent], Union[None, Awaitable[None]]]
EventFilter = Union[str, Sequence[str], Pattern[str], Callable[[CognitiveEvent], bool], None]


def match_event_type(pattern: str, event_type: str) -> bool:
    """
    Match an event_type against a string pattern.

    - Exact match unless pattern ends with '*'.
    - Trailing '*' means prefix match on the stem (e.g. "sensor.*" → "sensor.").
    """
    if not isinstance(pattern, str) or not pattern:
        return False
    if pattern.endswith("*"):
        prefix = pattern[:-1]
        return event_type.startswith(prefix)
    return event_type == pattern


@dataclass
class EventBusMetrics:
    published: int = 0
    delivered: int = 0
    # Legacy aggregate (incoming rejected under backpressure + other rejects)
    dropped: int = 0
    rejected: int = 0
    # Hardening counters (explicit)
    incoming_rejected: int = 0
    queued_evicted: int = 0
    expired_rejected: int = 0
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
            "incoming_rejected": self.incoming_rejected,
            "queued_evicted": self.queued_evicted,
            "expired_rejected": self.expired_rejected,
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
            return match_event_type(f, event.event_type)
        if isinstance(f, (list, tuple, set)):
            return any(match_event_type(str(p), event.event_type) for p in f)
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
    """Priority asyncio event bus for local cognitive runtime use."""

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

        Filtering:
          - exact type string
          - prefix with trailing '*' (e.g. "sensor.*")
          - list/tuple/set of patterns (each element uses the same rules)
          - compiled regex
          - predicate callable
        """
        sub = _Subscription(
            handler=handler,
            event_filter=event_type,
            name=name or getattr(handler, "__name__", ""),
        )
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

    def _reject_expired(self, event: CognitiveEvent, reason: str) -> None:
        self._record_dead_letter(event, reason)
        self._metrics.expired_rejected += 1
        self._metrics.rejected += 1

    def _reject_incoming(self, event: CognitiveEvent, reason: str) -> None:
        self._record_dead_letter(event, reason)
        self._metrics.incoming_rejected += 1
        self._metrics.rejected += 1
        self._metrics.dropped += 1

    def _evict_queued(self, event: CognitiveEvent, reason: str) -> None:
        self._record_dead_letter(event, reason)
        self._metrics.queued_evicted += 1
        self._metrics.dropped += 1

    def _peek_oldest_lowest_priority(self) -> Optional[tuple[EventPriority, CognitiveEvent]]:
        for priority in sorted(EventPriority):
            q = self._queues[priority]
            if q:
                return priority, q[0]
        return None

    def _try_admit_locked(self, event: CognitiveEvent) -> bool:
        """
        Admit event under backpressure policy. Caller holds lock when applicable.
        Returns True if admitted into a priority queue.
        """
        if self._depth < self.max_queue_size:
            self._queues[event.priority].append(event)
            self._depth += 1
            self._metrics.published += 1
            if self._depth > self._metrics.max_queue_depth:
                self._metrics.max_queue_depth = self._depth
            return True

        if not self.drop_on_full:
            self._reject_incoming(event, "backpressure_reject_no_drop")
            return False

        victim = self._peek_oldest_lowest_priority()
        if victim is None:
            self._reject_incoming(event, "backpressure_empty_but_full")
            return False

        victim_priority, victim_event = victim
        if int(event.priority) > int(victim_priority):
            # Evict oldest at lowest priority (FIFO within that priority).
            evicted = self._queues[victim_priority].popleft()
            self._depth = max(0, self._depth - 1)
            self._evict_queued(evicted, "backpressure_evicted_for_higher_priority")
            self._queues[event.priority].append(event)
            self._depth += 1
            self._metrics.published += 1
            if self._depth > self._metrics.max_queue_depth:
                self._metrics.max_queue_depth = self._depth
            return True

        # Equal or lower priority must not displace queued work.
        self._reject_incoming(event, "backpressure_incoming_not_higher_priority")
        return False

    async def publish(self, event: CognitiveEvent) -> bool:
        """Enqueue an event. Returns False if rejected under backpressure/expiry."""
        if self._closed:
            self._reject_incoming(event, "bus_closed")
            return False
        if not isinstance(event, CognitiveEvent):
            raise TypeError("publish expects CognitiveEvent")
        if event.is_expired():
            self._reject_expired(event, "expired_before_publish")
            return False

        if self._cond is None:
            self._cond = asyncio.Condition()

        async with self._cond:
            ok = self._try_admit_locked(event)
            if ok:
                self._cond.notify()
            return ok

    def publish_nowait(self, event: CognitiveEvent) -> bool:
        """Synchronous enqueue helper (does not dispatch)."""
        if self._closed:
            self._reject_incoming(event, "bus_closed")
            return False
        if not isinstance(event, CognitiveEvent):
            raise TypeError("publish_nowait expects CognitiveEvent")
        if event.is_expired():
            self._reject_expired(event, "expired_before_publish")
            return False
        return self._try_admit_locked(event)

    async def dispatch_inline(self, event: CognitiveEvent) -> bool:
        """
        Process an event immediately without enqueueing.

        Used by request/response cognitive-loop paths so completed requests
        never leave unconsumed queued events.
        """
        if self._closed:
            self._reject_incoming(event, "bus_closed")
            return False
        if not isinstance(event, CognitiveEvent):
            raise TypeError("dispatch_inline expects CognitiveEvent")
        if event.is_expired():
            self._reject_expired(event, "expired_before_dispatch")
            return False
        self._metrics.published += 1
        await self._dispatch(event)
        return True

    async def publish_and_dispatch(self, event: CognitiveEvent) -> bool:
        """Enqueue then immediately pull and dispatch the same event (no residual)."""
        ok = await self.publish(event)
        if not ok:
            return False
        popped = self._pop_event_by_id(event.event_id)
        if popped is None:
            return False
        await self._dispatch(popped)
        return True

    def _pop_event_by_id(self, event_id: str) -> Optional[CognitiveEvent]:
        for priority in sorted(EventPriority, reverse=True):
            q = self._queues[priority]
            for i, ev in enumerate(q):
                if ev.event_id == event_id:
                    del q[i]
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

    def queued_event_ids(self, priority: Optional[EventPriority] = None) -> List[str]:
        """Test helper: FIFO order of queued event ids (optionally one priority)."""
        if priority is not None:
            return [e.event_id for e in self._queues[priority]]
        out: List[str] = []
        for p in sorted(EventPriority, reverse=True):
            out.extend(e.event_id for e in self._queues[p])
        return out

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
            self._reject_expired(event, "expired_before_dispatch")
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
