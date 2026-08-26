"""
ORCA WebSocket Manager — Handles real-time agent progress streaming to the frontend.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time agent progress updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

    async def send_agent_progress(
        self,
        agent: str,
        status: str,
        message: str,
        data: Any = None,
    ):
        """Send an agent progress event."""
        event = {
            "type": "agent_progress",
            "agent": agent,
            "status": status,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast(event)


# Global manager instance
manager = ConnectionManager()
