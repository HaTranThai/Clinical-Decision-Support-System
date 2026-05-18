from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.ws_broadcaster import ws_broadcaster

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/live")
async def ws_live(
    ws: WebSocket,
    stay_id: str = Query(...),
    token: str | None = Query(default=None),
):
    await ws.accept()
    await ws_broadcaster.connect(stay_id, ws)

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await ws_broadcaster.disconnect(stay_id, ws)
