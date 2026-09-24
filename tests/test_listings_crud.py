from decimal import Decimal

from sqlalchemy import text

from app.db.session import engine


base_prefix = "/api/v1"

def _create(client, payload, **overrides):
    resp = client.post(f"{base_prefix}/listings", json={**payload, **overrides})
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_listing(client, payload):
    body = _create(client, payload)
    assert body["id"] == 1
    assert body["title"] == payload["title"]
    assert Decimal(body["price"]) == Decimal("1500000.00")
    assert body["location"] == {"lat": 4.8156, "lng": 7.0498}
    assert body["created_at"] and body["updated_at"]


def test_create_stores_geography_point(client, payload):
    _create(client, payload)
    with engine.connect() as conn:
        x, y = conn.execute(
            text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM listings")
        ).one()
    assert (x, y) == (7.0498, 4.8156)  # x = lng, y = lat


def test_create_validation_error_format(client, payload):
    resp = client.post(f"{base_prefix}/listings", json={**payload, "price": -1, "bedrooms": -2})
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    fields = {d["field"] for d in err["details"]}
    assert {"price", "bedrooms"} <= fields


def test_get_listing_and_404(client, payload):
    created = _create(client, payload)
    assert client.get(f"{base_prefix}/listings/{created['id']}").json() == created

    resp = client.get(f"{base_prefix}/listings/999")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_list_pagination(client, payload):
    for i in range(5):
        _create(client, payload, title=f"Listing {i}")

    resp = client.get(f"{base_prefix}/listings", params={"limit": 2, "offset": 2})
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 5
    assert (body["limit"], body["offset"]) == (2, 2)
    assert [i["title"] for i in body["items"]] == ["Listing 2", "Listing 3"]


def test_list_rejects_bad_pagination(client):
    assert client.get(f"{base_prefix}/listings", params={"limit": 0}).status_code == 422
    assert client.get(f"{base_prefix}/listings", params={"limit": 10_000}).status_code == 422
    assert client.get(f"{base_prefix}/listings", params={"offset": -1}).status_code == 422


def test_patch_partial_update(client, payload):
    created = _create(client, payload)
    resp = client.patch(f"{base_prefix}/listings/{created['id']}", json={"price": "1750000.00"})
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["price"]) == Decimal("1750000.00")
    assert body["title"] == created["title"]


def test_patch_location_keeps_geography_in_sync(client, payload):
    created = _create(client, payload)
    new_loc = {"lat": 6.5244, "lng": 3.3792}
    resp = client.patch(f"{base_prefix}/listings/{created['id']}", json={"location": new_loc})
    assert resp.json()["location"] == new_loc
    with engine.connect() as conn:
        x, y = conn.execute(
            text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM listings")
        ).one()
    assert (x, y) == (3.3792, 6.5244)


def test_patch_rejects_empty_and_null(client, payload):
    created = _create(client, payload)
    url = f"{base_prefix}/listings/{created['id']}"
    assert client.patch(url, json={}).status_code == 422
    assert client.patch(url, json={"price": None}).status_code == 422


def test_patch_missing_listing(client):
    assert client.patch(f"{base_prefix}/listings/42", json={"bedrooms": 3}).status_code == 404


def test_delete_listing(client, payload):
    created = _create(client, payload)
    url = f"{base_prefix}/listings/{created['id']}"
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404
