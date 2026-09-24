from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, cast
from sqlalchemy.orm import Session

from app.listing.models import Listing
from app.listing.schemas import (
    ListingCreate,
    ListingUpdate,
    Location,
    SearchParams,
)


def _point(loc: Location) -> WKTElement:
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


def update_listing(db: Session, listing: Listing, data: ListingUpdate) -> Listing:
    changes = data.model_dump(exclude_unset=True)
    loc = changes.pop("location", None)
    for field, value in changes.items():
        setattr(listing, field, value)
    if loc is not None:
        new_loc = Location(**loc)
        listing.latitude = new_loc.lat
        listing.longitude = new_loc.lng
        listing.location = _point(new_loc)
    db.commit()
    db.refresh(listing)
    return listing


def delete_listing(db: Session, listing: Listing) -> None:
    db.delete(listing)
    db.commit()


def search_listings(
    db: Session, params: SearchParams
) -> tuple[list[tuple[Listing, float | None]], int]:
    """Filter listings; returns ([(listing, distance_m | None)], total)."""
    filters = []
    if params.type is not None:
        filters.append(Listing.type == params.type)
    if params.min_price is not None:
        filters.append(Listing.price >= params.min_price)
    if params.max_price is not None:
        filters.append(Listing.price <= params.max_price)
    if params.bedrooms is not None:
        filters.append(Listing.bedrooms == params.bedrooms)
    if params.min_bedrooms is not None:
        filters.append(Listing.bedrooms >= params.min_bedrooms)
    if params.max_bedrooms is not None:
        filters.append(Listing.bedrooms <= params.max_bedrooms)

    if params.has_geo:
        point = cast(
            func.ST_SetSRID(func.ST_MakePoint(params.lng, params.lat), 4326),
            Geography,
        )
        distance = func.ST_Distance(Listing.location, point).label("distance_m")
        filters.append(
            func.ST_DWithin(Listing.location, point, params.radius_km * 1000)
        )
        stmt = select(Listing, distance).order_by(distance, Listing.id)
    else:
        stmt = select(Listing).order_by(Listing.id)

    total = db.scalar(select(func.count()).select_from(Listing).where(*filters)) or 0
    rows = db.execute(
        stmt.where(*filters).limit(params.limit).offset(params.offset)
    ).all()

    if params.has_geo:
        return [(r[0], float(r[1])) for r in rows], total
    return [(r[0], None) for r in rows], total
