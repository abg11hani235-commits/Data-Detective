import asyncio
from typing import AsyncGenerator, Dict, List


class EventBroadcaster:
    """
    Manages Server-Sent Events (SSE) queues per active session.
    Allows operational stages to stream to the client in real-time.
    """

    def __init__(self):
        self._queues: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        if session_id not in self._queues:
            self._queues[session_id] = []
        self._queues[session_id].append(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue) -> None:
        if session_id in self._queues:
            try:
                self._queues[session_id].remove(q)
            except ValueError:
                pass
            if not self._queues[session_id]:
                del self._queues[session_id]

    async def broadcast(self, session_id: str, event_type: str, stage: str, message: str, payload: dict = None) -> None:
        if session_id not in self._queues:
            return
        data = {
            "event_type": event_type,
            "stage": stage,
            "message": message,
            "payload": payload or {},
        }
        for q in self._queues[session_id]:
            await q.put(data)


broadcaster = EventBroadcaster()
