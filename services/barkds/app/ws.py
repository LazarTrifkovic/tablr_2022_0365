import asyncio
import json

from fastapi import WebSocket


class ConnectionManager:
    """Drži otvorene WebSocket konekcije bar dashboard-a, grupisane po kafiću."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, cafe_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(cafe_id, set()).add(ws)

    async def disconnect(self, cafe_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.get(cafe_id, set()).discard(ws)

    async def broadcast(self, cafe_id: str, event: dict) -> None:
        message = json.dumps(event, ensure_ascii=False, default=str)
        stale: list[WebSocket] = []
        for ws in list(self._connections.get(cafe_id, set())):
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(cafe_id, ws)


manager = ConnectionManager()
