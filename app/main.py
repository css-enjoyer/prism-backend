from fastapi import FastAPI
from .config import settings
from .routers.webhook import app as webhook_router

app = FastAPI()
app.include_router(webhook_router)
# uv run uvicorn app.main:app --reload

@app.get("/health")
async def health():
    return {
        "app_name": settings.app_name,
        "status": "ok"
    }

