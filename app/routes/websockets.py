from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.websockets import ws_manager

router = APIRouter()

@router.websocket("/update_coords")
async def update_coords(ws: WebSocket):
    await ws_manager.connect(ws)

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
