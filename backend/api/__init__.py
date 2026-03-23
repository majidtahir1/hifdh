"""
Hifdh Review App - API

This module contains REST API routes and WebSocket handlers.
"""

from .routes import router
from .websocket import websocket_router

__all__ = [
    "router",
    "websocket_router",
]
