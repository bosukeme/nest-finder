from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.listing import services as svc
from app.listing.schemas import (
    ListingCreate,
    ListingRead,
    ListingSearchRead,
    ListingUpdate,
    Page,
    SearchParams,
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Listing {listing_id} not found")
    return listing


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, db: DB):
    return svc.create_listing(db, payload)


@router.get("", response_model=Page[ListingRead])
def list_listings(db: DB, page: Pagination):
    rows, total = svc.list_listings(db, limit=page.limit, offset=page.offset)
    return Page[ListingRead](items=rows, total=total, limit=page.limit, offset=page.offset)


@router.get("/search", response_model=Page[ListingSearchRead])
def search_listings(db: DB, params: Annotated[SearchParams, Query()]):
    """Filter by type, price range and bedrooms; optionally restrict to
    listings within `radius_km` of (`lat`, `lng`), nearest first."""
    rows, total = svc.search_listings(db, params)
    items = [
        ListingSearchRead(
            **ListingRead.model_validate(listing).model_dump(),
            distance_km=None if dist_m is None else round(dist_m / 1000, 3),
        )
        for listing, dist_m in rows
    ]
    return Page[ListingSearchRead](items=items, total=total, limit=params.limit, offset=params.offset)


@router.get("/{listing_id}", response_model=ListingRead)
def get_listing(listing_id: int, db: DB):
    return _get_or_404(db, listing_id)


@router.patch("/{listing_id}", response_model=ListingRead)
def update_listing(listing_id: int, payload: ListingUpdate, db: DB):
    listing = _get_or_404(db, listing_id)
    return svc.update_listing(db, listing, payload)


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: DB):
    listing = _get_or_404(db, listing_id)
    svc.delete_listing(db, listing)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
