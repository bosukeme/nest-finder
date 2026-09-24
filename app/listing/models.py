import enum
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geography
from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ListingType(str, enum.Enum):
    rent = "rent"
    sale = "sale"
    shortlet = "shortlet"


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_listings_price_positive"),
        CheckConstraint("bedrooms >= 0", name="ck_listings_bedrooms_nonneg"),
        Index("ix_listings_type_price", "type", "price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    type: Mapped[ListingType] = mapped_column(Enum(ListingType, name="listing_type"))
    bedrooms: Mapped[int] = mapped_column(index=True)

    latitude: Mapped[float]
    longitude: Mapped[float]
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    agent_id: Mapped[int] = mapped_column(index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
