from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSBroadcaster:

    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, stay_id: str, ws: WebSocket):
        async with self._lock:
            if stay_id not in self._connections:
                self._connections[stay_id] = set()
            self._connections[stay_id].add(ws)
        logger.info(f"WS client connected to stay {stay_id[:8]}... (total: {len(self._connections.get(stay_id, set()))})")

    async def disconnect(self, stay_id: str, ws: WebSocket):
        async with self._lock:
            if stay_id in self._connections:
                self._connections[stay_id].discard(ws)
                if not self._connections[stay_id]:
                    del self._connections[stay_id]
        logger.info(f"WS client disconnected from stay {stay_id[:8]}...")

    async def broadcast(self, stay_id: str, message_type: str, data: dict):
        if stay_id not in self._connections:
            return

        payload = json.dumps({"type": message_type, "data": data})
        dead = set()

        for ws in self._connections.get(stay_id, set()).copy():
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)

        if dead:
            async with self._lock:
                if stay_id in self._connections:
                    self._connections[stay_id] -= dead

    async def broadcast_all(self, message_type: str, data: dict):
        for stay_id in list(self._connections.keys()):
            await self.broadcast(stay_id, message_type, data)

    @property
    def active_stays(self) -> list[str]:
        return list(self._connections.keys())


ws_broadcaster = WSBroadcaster()
