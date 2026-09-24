from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import APIRouter, FastAPI
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)


def set_up_limiter(app: FastAPI):
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)


def apply_rate_limit_to_router(router: APIRouter, rate: str):
    for route in router.routes:
        if hasattr(route.endpoint, "__call__"):
            route.endpoint = limiter.limit(rate)(route.endpoint)
