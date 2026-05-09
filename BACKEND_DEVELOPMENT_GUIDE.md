# MeramotHub Backend — Development Guide & Progress

## What happened so far

- Environment: `.env` found with `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, JWT settings.
- DB connectivity: Verified successful connection to Supabase Postgres (ran `SELECT 1` → `1`).
- Server: FastAPI app started with Uvicorn at `http://127.0.0.1:8000`.
- Auth flow tested via CLI/urllib:
  - `POST /auth/register` — returned `201` and user JSON.
  - `POST /auth/login` — returned `200` and JWT access token.
  - `GET /auth/me` — returned authenticated user when using `Authorization: Bearer <token>`.
- Fixes applied to start the app:
  - `app/models/service_provider.py`: imported missing `Numeric` and `Boolean`.
  - `app/routers/bookings.py`: added imports `UUID`, `get_current_user`, and `release_payment`.
- Test data: A test customer user was created during manual tests (can be removed via DB).

## Current status (now)

- FastAPI server: running locally on port 8000.
- Database: connected and operational.
- Authentication: registration, login, and token-based `me` endpoint work.
- Remaining work: implement and wire up pages 1–13 as detailed in the original plan (see "Planned tasks").

## Commands run (reproducible)

```powershell
# Start server
f:/MeramotHub/backend/venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Quick programmatic tests were performed with Python urllib.request (examples):
# register -> login -> get /auth/me (handled inside test script)
```

## Files modified during initial testing

- [app/models/service_provider.py](app/models/service_provider.py#L1-L200) — added `Numeric` and `Boolean` imports.
- [app/routers/bookings.py](app/routers/bookings.py#L1-L40) — added `UUID`, `get_current_user`, and `release_payment` imports.

## What will happen next (AI-friendly plan)

This section maps the provided 13-page spec into a prioritized, machine-readable plan. Each step is actionable, idempotent where possible, and references files or endpoints to create.

1. Project bootstrap
   - Ensure files: `app/config.py`, `app/database.py`, `app/main.py`, `requirements.txt`, `.env`.
   - Validate environment variables are loaded.

2. User & Auth (Page 2)
   - Implement `app/models/user.py` with `User` SQLAlchemy model (UUID PK).
   - Implement `app/schemas/user.py` with registration/login/response schemas.
   - Implement `app/utils/auth.py` (hash, verify, JWT, dependency).
   - Implement `app/routers/auth.py` with `/auth/register`, `/auth/login`, `/auth/me`.
   - Add tests via Swagger manual flow and automated CLI scripts.

3. Service Provider Profile & Verification (Page 3)
   - Model: `ServiceProviderProfile` with enums and verification fields.
   - Schemas and router endpoints under `app/routers/service_providers.py`.
   - Implement `require_role()` utility.

4. Service Catalogue & Pricing (Page 4)
   - Models: `ServiceCategory`, `ServiceItem`.
   - Admin-protected routes to create categories and items.
   - Seed script to create initial categories and items.

5. Booking System (Page 5)
   - Model: `Booking` and schemas.
   - Customer & provider endpoints: create, accept, start, complete, cancel.
   - Ensure `total_price` copies `ServiceItem.base_price` at booking time.

6. Escrow Payment System (Page 6)
   - Model: `Payment` with commission calculations.
   - Endpoints: pay (hold), release, refund, provider earnings.
   - Hook `release_payment()` into booking completion.

7. Geo search and availability (Page 7)
   - Add `current_latitude`, `current_longitude`, `is_available`, `last_seen_at` to provider profile.
   - Implement `app/services/geo.py` with `haversine_distance()`.
   - Add endpoints to update availability/location and search nearby providers.

8. Ratings & Reviews (Page 8)
   - Model: `Review` and review endpoints.
   - Recompute provider `rating_avg` and `rating_count` after new reviews.

9. Complaint System (Page 9)
   - Model and endpoints to file, assign, resolve complaints.
   - Integrate with payment utilities for refunds/releases.

10. Admin & Area Manager dashboards (Page 10)
    - Aggregation endpoints for stats and admin actions.

11. AI Chatbot & Real-time chat (Page 11)
    - Chatbot endpoint using OpenAI/Anthropic (placeholder) and rate limiting.
    - WhatsApp URL send helper.

12. Priyo Workshop & Instant Booking (Page 12)
    - Subscription model and `require_pro` dependency.
    - Priyo endpoints and instant booking flow with auto-assignment.

13. Final polish (Page 13)
    - Global exception handlers, request logging middleware, pagination utility.
    - Standardize response schema wrappers.
    - Seed script and Alembic initial migration.

## Swagger testing checklist (short)

- Register → Login → Authorize (paste JWT) → test protected endpoints.
- Test provider verification flow (area_manager role required).
- Test booking lifecycle with payments and release/refund logic.

## Notes & Recommendations

- Backup `.env` secrets before committing. Remove `SUPABASE_KEY` publishable keys from public repos.
- Consider creating a database-migration-safe seed script and an admin CLI for creating admin/area_manager users.
- Add unit tests for `auth`, `payments`, and `geo` utilities.

---

If you want, I can now:
- Commit the fixes I applied and create a local git remote commit message.
- Remove the test user from the DB.
- Begin implementing Page 3 (service provider flows) next.


