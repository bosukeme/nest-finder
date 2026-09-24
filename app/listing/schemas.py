from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
        # The ORM row stores flat latitude/longitude; the API exposes them
        # as a nested `location` object.
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
