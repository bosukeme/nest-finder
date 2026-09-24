import pytest
from pydantic import ValidationError

from app.listing.schemas import ListingCreate, ListingUpdate

VALID = {
    "title": "  2-bed apartment, GRA  ",
    "price": "1500000.50",
    "type": "rent",
    "bedrooms": 2,
    "location": {"lat": 4.8156, "lng": 7.0498},
    "agent_id": 1,
}


def test_create_valid_strips_title():
    listing = ListingCreate(**VALID)
    assert listing.title == "2-bed apartment, GRA"


@pytest.mark.parametrize(
    "patch",
    [
        {"price": 0},
        {"price": -5},
        {"price": "10.999"},
        {"type": "lease"},
        {"bedrooms": -1},
        {"title": "   "},
        {"agent_id": 0},
        {"location": {"lat": 91, "lng": 0}},
        {"location": {"lat": 0, "lng": 181}},
        {"unknown_field": 1},
    ],
)
def test_create_rejects_invalid(patch):
    with pytest.raises(ValidationError):
        ListingCreate(**{**VALID, **patch})


def test_update_requires_a_field():
    with pytest.raises(ValidationError):
        ListingUpdate()


def test_update_rejects_explicit_null():
    with pytest.raises(ValidationError):
        ListingUpdate(price=None)


def test_update_partial_ok():
    upd = ListingUpdate(price="900000")
    assert upd.model_dump(exclude_unset=True) == {"price": upd.price}
