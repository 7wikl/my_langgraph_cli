"""FastAPI application entry point."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_app.config.settings import settings
from ai_app.api.routes import router

app = FastAPI(
    title="Fin Agent API",
    description="Chinese A-share market investment advisor powered by LangGraph",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {
        "name": "Fin Agent API",
        "version": "0.1.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    host = settings.HOST
    port = settings.PORT
    uvicorn.run("ai_app.main:app", host=host, port=port, reload=True)
