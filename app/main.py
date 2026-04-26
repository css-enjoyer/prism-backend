from fastapi import FastAPI
from .config import settings
from .routers.webhook import router as webhook_router
from .routers.analysis import router as analysis_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.include_router(webhook_router)
app.include_router(analysis_router)

# uv run uvicorn app.main:app --reload

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"app_name": settings.app_name, "status": "ok"}
