from fastapi import FastAPI

from app.middlewares.cors_trusted_host import set_up_cors, set_up_trusted_host
from app.middlewares.logging import set_up_logging
from app.middlewares.rate_limit import set_up_limiter


def register_middleware(app: FastAPI):
    set_up_limiter(app)
    set_up_cors(app)
    set_up_trusted_host(app)
    set_up_logging(app)
