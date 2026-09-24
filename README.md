# Nest Finder

A small property listings API: CRUD for listings, filtered search, and
"within X km of this point" search. Built with FastAPI, SQLAlchemy 2.0,
Alembic and Postgres/PostGIS.

## Setup

### With Docker

```bash
cp .env.example .env
docker compose up --build
docker compose run --rm api python -m app.scripts.seed   # optional sample data
```

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Migrations run automatically when the `api` container starts.

### Without Docker

You need Python 3.12+ and a Postgres instance with PostGIS available.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # adjust DATABASE_URL if needed
alembic upgrade head
uvicorn app.main:app --reload
```

### Tests

```bash
docker compose up -d db
docker compose run --rm api pytest -q
```

Tests run against a separate `nestfinder_test` database (created by
`scripts/init-db.sql`) and use real PostGIS, not mocks. Migrations are applied
once per session and the table is truncated between tests.

- `tests/test_schemas.py`: validation rules (unit)
- `tests/test_listings_crud.py`: CRUD, pagination, error format, geography kept in sync (integration)
- `tests/test_search.py`: every filter, radius search with known distances, ordering, invalid params (integration)

## API

| Method | Path | Notes |
|---|---|---|
| POST | `/api/v1/listings` | 201 on success |
| GET | `/api/v1/listings?limit=&offset=` | paginated |
| GET | `/api/v1/listings/{id}` | 404 if missing |
| PATCH | `/api/v1/listings/{id}` | partial update; body needs at least one field |
| DELETE | `/api/v1/listings/{id}` | 204 |
| GET | `/api/v1/listings/search` | filters + radius search |

### Example

```bash
curl -X POST localhost:8000/api/v1/listings -H 'content-type: application/json' -d '{
  "title": "Modern 3-bed flat, GRA Phase 2",
  "price": "4500000.00",
  "type": "rent",
  "bedrooms": 3,
  "location": {"lat": 4.8156, "lng": 7.0498},
  "agent_id": 1
}'
```

### Search

```bash
curl "localhost:8000/api/v1/listings/search?type=rent&min_price=500000&max_price=5000000&min_bedrooms=2&lat=4.8156&lng=7.0498&radius_km=5&limit=10"
```

| Param | Notes |
|---|---|
| `type` | `rent`, `sale` or `shortlet` |
| `min_price`, `max_price` | inclusive; min must be <= max |
| `bedrooms` | exact match; cannot be combined with the range params |
| `min_bedrooms`, `max_bedrooms` | inclusive range |
| `lat`, `lng`, `radius_km` | must be sent together (radius 0-500 km). Results are sorted nearest first and include `distance_km` |
| `limit`, `offset` | default 20, max 100. `total` counts all matches, not just the page |

Without a point, results are ordered by id and `distance_km` is null.

### Response shapes

Pages: `{"items": [...], "total": 42, "limit": 20, "offset": 0}`

Errors all look the same:

```json
{"error": {"code": "validation_error", "message": "Request validation failed",
           "details": [{"field": "price", "message": "Input should be greater than 0"}]}}
```

Codes: `validation_error` (422), `not_found` (404), `internal_error` (500, no internals leaked).

## Design choices

**FastAPI over Django.** The scope is a small API where validation and docs
matter most. Pydantic gives request validation and OpenAPI docs almost for
free. Django + GeoDjango would also work, but needs GDAL/GEOS installed
locally, which makes the project harder for a reviewer to run.

**Postgres + PostGIS for the radius search.** The location is stored as a
`geography(Point, 4326)` with a GiST index, and the search uses `ST_DWithin`,
which works in metres on a sphere and can use the index. The alternative without PostGIS
is a bounding-box prefilter plus haversine, which is fine at small scale but
needs more hand-written maths.

**Lat/lng stored twice.** `latitude`/`longitude` are plain columns and
`location` is the spatial column. Plain columns keep reads and debugging simple;
the spatial column powers search.

**Modular Layering.** `routes.py` handle HTTP, `services.py` holds the business logic and queries, `models.py` is
the database, `schemas.py` is the API contract.

**Validation.** Pydantic rejects bad input with clear messages
(price > 0 with two decimals, bedrooms 0-50, coordinate ranges, blank titles,
unknown fields). The database also has CHECK constraints for price and
bedrooms as a backstop.

**Money as Decimal.** Stored as `NUMERIC(14,2)`, so there is no float rounding.
Pydantic serialises it as a string (`"4500000.00"`).

**Offset pagination.** It is simple, supports jumping to a page and returns a
total count.

**Consistent errors.** One error shape for validation errors, 404s and
unexpected failures.


## What I would improve with more time

- **Agents:** a real `agents` table with a foreign key, and validation that the
  agent exists.
- **Auth and ownership:** only the listing's agent can edit or delete it.
- **Pagination:** keyset (cursor) pagination for deep pages and stable results;
  optionally skip the `COUNT` on large tables.
- **Soft deletes** and an audit trail instead of hard deletes.
- **Operations:** a non-root multi-stage Dockerfile, and a
  proper readiness probe.
- **API polish:** bulk import.
