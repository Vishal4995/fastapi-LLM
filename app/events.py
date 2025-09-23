import asyncio
import json
from typing import Any


class SSEBroker:
    """In-memory SSE broadcaster that fan-outs events to connected subscribers."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, str]]] = set()
        self._lock = asyncio.Lock()
        self._seq = 0

    async def subscribe(self) -> asyncio.Queue[dict[str, str]]:
        queue: asyncio.Queue[dict[str, str]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, str]]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def publish(self, event: str, data: Any) -> None:
        if isinstance(data, str):
            payload_data = data
        else:
            payload_data = json.dumps(data, default=str)

        async with self._lock:
            if not self._subscribers:
                return
            self._seq += 1
            event_id = str(self._seq)
            subscribers = list(self._subscribers)

        message = {"event": event, "id": event_id, "data": payload_data}

        for queue in subscribers:
            await queue.put(message)


item_event_broker = SSEBroker()
