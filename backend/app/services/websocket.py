"""In-memory WebSocket connection registry.

Note: this works for a single server process. Running several workers/instances would need a
shared broker (e.g. Redis pub/sub) so that every instance can reach every connected user.
"""
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger("bloodbridge.ws")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        conns = self.active_connections.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)
        if conns is not None and not conns:
            self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: dict, user_id: int):
        for connection in list(self.active_connections.get(user_id, [])):
            try:
                await connection.send_json(message)
            except Exception:  # connection already closed
                self.disconnect(user_id, connection)

    async def broadcast(self, message: dict):
        for user_id, connections in list(self.active_connections.items()):
            for connection in list(connections):
                try:
                    await connection.send_json(message)
                except Exception:
                    self.disconnect(user_id, connection)


manager = ConnectionManager()
