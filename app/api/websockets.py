from fastapi import WebSocket
import functools
from typing import Callable, Awaitable

class ConnectionManager():

    def __init__(self) -> None:
        self._active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self._active_connections.remove(ws)

    async def broadcast(self, message: str) -> None:
        print("Websocket procesa mensaje")
        for connection in self._active_connections:
            await connection.send_text(message)

    def notify_update_to_client(self, callback: Callable[..., Awaitable]):

        @functools.wraps(callback)
        async def wrapper(*args, **kwargs):
            response = await callback(*args, **kwargs)

            await self.broadcast('update')

            return response

        return wrapper

ws_manager = ConnectionManager()
