from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.seed_data import seed_database_if_empty
from app.db.session import Base, SessionLocal, engine
from app.routers import ai, auth, dashboard, patients


def ensure_db_initialized() -> None:
    """Create tables and seed sample data idempotently for ASGI and serverless cold starts."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()


ensure_db_initialized()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_db_initialized()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AI-Assisted Medical Record Database — Relational Patient & Clinical Encounter Management "
        "with Citation-Grounded AI Summarisation and Natural-Language Historical Retrieval. "
        "Developed by Pushkar Panwar (2501730022) & Saksham Singh (2501730270)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(patients.router)
app.include_router(ai.router)


@app.get("/api/health", tags=["System Health"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "team": [
            {"name": "Pushkar Panwar", "roll_no": "2501730022"},
            {"name": "Saksham Singh", "roll_no": "2501730270"},
        ],
    }
