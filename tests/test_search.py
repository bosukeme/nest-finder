import pytest

CENTER = {"lat": 4.8156, "lng": 7.0498}

base_prefix = "/api/v1"


def _mk(client, title, *, lat, lng, price="1000000", type="rent", bedrooms=2, agent_id=1):
    resp = client.post(
        f"{base_prefix}/listings",
        json={
            "title": title,
            "price": price,
            "type": type,
            "bedrooms": bedrooms,
            "location": {"lat": lat, "lng": lng},
            "agent_id": agent_id,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def seeded(client):
    _mk(client, "at-center", lat=4.8156, lng=7.0498, price="1000000", type="rent", bedrooms=2)
    _mk(client, "1km-north", lat=4.8256, lng=7.0498, price="2000000", type="sale", bedrooms=3)
    _mk(client, "5km-north", lat=4.8656, lng=7.0498, price="500000", type="shortlet", bedrooms=1)
    _mk(client, "lagos", lat=6.5244, lng=3.3792, price="3000000", type="rent", bedrooms=4)


def _titles(resp):
    assert resp.status_code == 200, resp.text
    return [i["title"] for i in resp.json()["items"]]


def test_no_filters_returns_everything(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search")
    assert resp.json()["total"] == 4
    assert all(i["distance_km"] is None for i in resp.json()["items"])


def test_filter_by_type(client, seeded):
    assert _titles(client.get(f"{base_prefix}/listings/search", params={"type": "rent"})) == [
        "at-center",
        "lagos",
    ]


def test_filter_by_price_range(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={"min_price": 900000, "max_price": 2000000})
    assert _titles(resp) == ["at-center", "1km-north"]


def test_filter_by_exact_bedrooms(client, seeded):
    assert _titles(client.get(f"{base_prefix}/listings/search", params={"bedrooms": 3})) == ["1km-north"]


def test_filter_by_bedroom_range(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={"min_bedrooms": 2, "max_bedrooms": 3})
    assert _titles(resp) == ["at-center", "1km-north"]


def test_radius_search_sorted_by_distance(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={**CENTER, "radius_km": 10})
    assert _titles(resp) == ["at-center", "1km-north", "5km-north"]
    d = [i["distance_km"] for i in resp.json()["items"]]
    assert d[0] == pytest.approx(0, abs=0.01)
    assert d[1] == pytest.approx(1.11, abs=0.05)
    assert d[2] == pytest.approx(5.56, abs=0.05)


def test_radius_excludes_outside(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={**CENTER, "radius_km": 2})
    assert _titles(resp) == ["at-center", "1km-north"]


def test_radius_combined_with_filters(client, seeded):
    resp = client.get(
        f"{base_prefix}/listings/search", params={**CENTER, "radius_km": 10, "type": "shortlet", "max_price": 600000}
    )
    assert _titles(resp) == ["5km-north"]


def test_pagination_total_reflects_all_matches(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={**CENTER, "radius_km": 10, "limit": 1, "offset": 1})
    body = resp.json()
    assert body["total"] == 3
    assert [i["title"] for i in body["items"]] == ["1km-north"]


def test_no_matches_returns_empty_page(client, seeded):
    resp = client.get(f"{base_prefix}/listings/search", params={"type": "sale", "bedrooms": 9})
    assert resp.status_code == 200
    assert resp.json()["items"] == [] and resp.json()["total"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 4.8, "lng": 7.0},
        {"radius_km": 5},
        {"lat": 4.8, "lng": 7.0, "radius_km": 0},
        {"lat": 4.8, "lng": 7.0, "radius_km": 9999},
        {"lat": 95, "lng": 7.0, "radius_km": 5},
        {"min_price": 500, "max_price": 100},
        {"min_price": -1},
        {"bedrooms": 2, "min_bedrooms": 1},
        {"min_bedrooms": 4, "max_bedrooms": 1},
        {"type": "lease"},
        {"limit": 0},
    ],
)
def test_invalid_search_params(client, params):
    resp = client.get(f"{base_prefix}/listings/search", params=params)
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert err["details"]


def test_search_route_not_shadowed_by_id_route(client):
    assert client.get(f"{base_prefix}/listings/search").status_code == 200
