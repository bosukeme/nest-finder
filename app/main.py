from fastapi import FastAPI
from app.middlewares import register_middleware
from app.listing.routes import router as listings


app = FastAPI(
    title="Nest Finder API",
    description="Property listings",
    version="0.1.0",
)

base_prefix = "/api/v1"

register_middleware(app)

app.include_router(listings, prefix=f"{base_prefix}/listings", tags=["listings"])


@app.get("/")
def home():
    return "Welcome to the Nest Finder API"
