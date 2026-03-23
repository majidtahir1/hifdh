"""
Hifdh Review App - FastAPI Application Entry Point

This is the main entry point for the FastAPI backend application.
It configures CORS, includes API routes, and sets up the WebSocket handler.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.websocket import websocket_router
from services.quran_data import get_quran_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Performs startup and shutdown tasks:
    - Startup: Load Quran data into memory
    - Shutdown: Cleanup resources
    """
    # Startup: Load Quran data
    print("Loading Quran data...")
    quran_service = get_quran_service()
    print(f"Loaded {quran_service.get_total_ayahs()} ayahs")

    yield

    # Shutdown: Cleanup (if needed)
    print("Shutting down Hifdh Review App...")


# Create FastAPI application
app = FastAPI(
    title="Hifdh Review App",
    description="A Quran memorization review application with real-time feedback",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
# In production, restrict origins to your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Vite dev server
        "http://localhost:5173",      # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Include WebSocket routes
app.include_router(websocket_router)


@app.get("/")
async def root():
    """Root endpoint with application info."""
    return {
        "name": "Hifdh Review App",
        "version": "1.0.0",
        "description": "Quran memorization review with real-time feedback",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
