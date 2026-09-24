from fastapi import FastAPI
from app.errors import register_exception_handlers
from app.middlewares import register_middleware
from app.listing.routes import router as listings

from sqlalchemy import text

from app.db.session import engine


app = FastAPI(
    title="Nest Finder API",
    description="Property listings",
    version="0.1.0",
)

base_prefix = "/api/v1"

register_exception_handlers(app)
register_middleware(app)

app.include_router(listings, prefix=f"{base_prefix}/listings", tags=["listings"])


@app.get("/")
def home():
    return "Welcome to the Nest Finder API"


@app.get("/health", tags=["meta"])
def health() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
