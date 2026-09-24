from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.listing.models import Listing
from app.listing.schemas import ListingCreate, Location


def _point(loc: Location) -> WKTElement:
    # WKT is (x y) = (lng lat)
    return WKTElement(f"POINT({loc.lng} {loc.lat})", srid=4326)


def create_listing(db: Session, data: ListingCreate) -> Listing:
    listing = Listing(
        title=data.title,
        price=data.price,
        type=data.type,
        bedrooms=data.bedrooms,
        latitude=data.location.lat,
        longitude=data.location.lng,
        location=_point(data.location),
        agent_id=data.agent_id,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def get_listing(db: Session, listing_id: int) -> Listing | None:
    return db.get(Listing, listing_id)


def list_listings(db: Session, *, limit: int, offset: int) -> tuple[list[Listing], int]:
    total = db.scalar(select(func.count()).select_from(Listing)) or 0
    rows = db.scalars(
        select(Listing).order_by(Listing.id).limit(limit).offset(offset)
    ).all()
    return list(rows), total
