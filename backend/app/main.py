from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    analytics,
    auth,
    categorize,
    credit_purchases,
    imports,
    lookups,
    transactions,
)
from app.routers import (
    settings as settings_router,
)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(credit_purchases.router, prefix="/api")
app.include_router(lookups.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(imports.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(categorize.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
