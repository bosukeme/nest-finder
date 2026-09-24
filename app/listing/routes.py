from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session


from app.config import settings
from app.listing import services as svc
from app.db.session import get_db
from app.listing.schemas import (
    ListingCreate,
    ListingRead,
    Page,
)

router = APIRouter()

DB = Annotated[Session, Depends(get_db)]


class PageParams:
    def __init__(
        self,
        limit: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
        offset: int = Query(0, ge=0),
    ):
        self.limit = limit
        self.offset = offset


Pagination = Annotated[PageParams, Depends()]


def _get_or_404(db: Session, listing_id: int):
    listing = svc.get_listing(db, listing_id)
    if listing is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"Listing {listing_id} not found"
        )
    return listing


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, db: DB):
    return svc.create_listing(db, payload)


@router.get("", response_model=Page[ListingRead])
def list_listings(db: DB, page: Pagination):
    rows, total = svc.list_listings(db, limit=page.limit, offset=page.offset)
    return Page[ListingRead](
        items=rows, total=total, limit=page.limit, offset=page.offset
    )
