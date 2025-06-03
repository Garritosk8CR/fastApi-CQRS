from fastapi import WebSocket
import asyncio

class SubscriptionConnectionManager:
    def __init__(self):
        # Dictionary mapping user_id to a list of active websocket connections.
        self.active_connections: dict[int, list[WebSocket]] = {}