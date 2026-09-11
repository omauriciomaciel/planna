from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.config import settings
from app.finance import router as finance_router
from app.schemas import HealthRead

app = FastAPI(title="Planna API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(auth_router)
app.include_router(finance_router)


@app.get("/health", tags=["operation"])
def health() -> HealthRead:
    return HealthRead(status="ok")
