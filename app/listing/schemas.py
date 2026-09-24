from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.config import settings
from app.listing.models import ListingType

T = TypeVar("T")


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90, examples=[4.8156])
    lng: float = Field(ge=-180, le=180, examples=[7.0498])


def _clean_title(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("title must not be blank")
    return v


class ListingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    type: ListingType
    bedrooms: int = Field(ge=0, le=50)
    location: Location
    agent_id: int = Field(gt=0)

    _strip_title = field_validator("title")(_clean_title)


class ListingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: Decimal
    type: ListingType
    bedrooms: int
    location: Location
    agent_id: int
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _from_orm(cls, data: Any) -> Any:
        if hasattr(data, "latitude"):
            return {
                "id": data.id,
                "title": data.title,
                "price": data.price,
                "type": data.type,
                "bedrooms": data.bedrooms,
                "location": {"lat": data.latitude, "lng": data.longitude},
                "agent_id": data.agent_id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ListingUpdate(BaseModel):

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    type: ListingType | None = None
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    location: Location | None = None
    agent_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str | None) -> str | None:
        return None if v is None else _clean_title(v)

    @model_validator(mode="after")
    def _check_fields(self) -> "ListingUpdate":
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        nulls = [f for f in self.model_fields_set if getattr(self, f) is None]
        if nulls:
            raise ValueError(f"fields cannot be null: {', '.join(sorted(nulls))}")
        return self


class SearchParams(BaseModel):
    """Query parameters for GET /listings/search."""

    model_config = ConfigDict(extra="forbid")

    type: ListingType | None = None
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    bedrooms: int | None = Field(default=None, ge=0, le=50, description="Exact match")
    min_bedrooms: int | None = Field(default=None, ge=0, le=50)
    max_bedrooms: int | None = Field(default=None, ge=0, le=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=500)

    limit: int = Field(
        default=settings.default_page_size, ge=1, le=settings.max_page_size
    )
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _cross_field_checks(self) -> "SearchParams":
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("min_price cannot be greater than max_price")

        if self.bedrooms is not None and (
            self.min_bedrooms is not None or self.max_bedrooms is not None
        ):
            raise ValueError(
                "use either bedrooms or min_bedrooms/max_bedrooms, not both"
            )
        if (
            self.min_bedrooms is not None
            and self.max_bedrooms is not None
            and self.min_bedrooms > self.max_bedrooms
        ):
            raise ValueError("min_bedrooms cannot be greater than max_bedrooms")

        geo = (self.lat, self.lng, self.radius_km)
        if any(v is not None for v in geo) and not all(v is not None for v in geo):
            raise ValueError("lat, lng and radius_km must be provided together")
        return self

    @property
    def has_geo(self) -> bool:
        return self.lat is not None


class ListingSearchRead(ListingRead):
    distance_km: float | None = None
