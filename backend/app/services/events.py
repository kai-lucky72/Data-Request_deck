"""Small in-process event broker for live UI refresh signals."""

import asyncio
import json
import threading
from collections.abc import AsyncIterator


class EventBroker:
    """Broadcast lightweight invalidation messages to connected SSE clients.

    Compose runs one API process, so an in-memory broker is sufficient. Messages
    contain no record data; the browser reloads through the normal authorized API.
    """

    def __init__(self) -> None:
        self._subscribers: dict[asyncio.Queue[str], asyncio.AbstractEventLoop] = {}
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1)
        with self._lock:
            self._subscribers[queue] = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue[str]) -> None:
        with self._lock:
            self._subscribers.pop(queue, None)

    def publish(self, event_type: str) -> None:
        message = json.dumps({"type": event_type}, separators=(",", ":"))
        with self._lock:
            subscribers = list(self._subscribers.items())
        for queue, loop in subscribers:
            if loop.is_closed():
                self.unsubscribe(queue)
                continue
            loop.call_soon_threadsafe(self._put_latest, queue, message)

    @staticmethod
    def _put_latest(queue: asyncio.Queue[str], message: str) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    async def stream(self, queue: asyncio.Queue[str]) -> AsyncIterator[str]:
        yield "retry: 2000\n\n"
        try:
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"event: update\ndata: {message}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe(queue)


event_broker = EventBroker()
