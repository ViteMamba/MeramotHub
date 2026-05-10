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

## Current status (now) — ALL BACKEND PAGES COMPLETE ✅

All 13 pages from the original spec have been implemented. The backend is feature-complete.

### Bug fixes applied
1. ✅ Fixed double-commit in `payment_service.py` — removed internal `db.commit()` from `release_payment()` and `refund_payment()`.
2. ✅ Fixed role enum comparison in `roles.py` — normalized string/enum comparison.
3. ✅ Added `email-validator` to `requirements.txt`.
4. ✅ Added model auto-import + `create_all()` in `main.py` startup event.
5. ✅ Made `seed_services.py` idempotent (safe to run multiple times).
6. ✅ Standardized all Pydantic schemas to v2 (`model_config` instead of `class Config`).

### Features implemented

| # | Feature | Status | Key Endpoints |
|---|---------|--------|---------------|
| 1 | Project Bootstrap | ✅ | `config.py`, `database.py`, `main.py` |
| 2 | User & Auth | ✅ | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| 3 | Provider Profile & Verification | ✅ | `POST /providers/profile`, `GET /providers/profile/me`, `PATCH /{id}/verify` |
| 4 | Service Catalogue | ✅ | `POST /services/categories`, `POST /services/items`, `GET /services/items` |
| 5 | Booking System | ✅ | `POST /bookings/`, `PATCH /{id}/accept`, `/start`, `/complete`, `/cancel` |
| 6 | Escrow Payments | ✅ | `POST /payments/pay`, `POST /{id}/refund`, `GET /payments/earnings` |
| 7 | Geo Search & Availability | ✅ | `PATCH /providers/profile/location`, `GET /providers/nearby` |
| 8 | Ratings & Reviews | ✅ | `POST /reviews/`, `GET /reviews/provider/{id}`, `GET /reviews/my` |
| 9 | Complaint System | ✅ | `POST /complaints/`, `PATCH /{id}/assign`, `PATCH /{id}/resolve` |
| 10 | Admin & Area Manager Dashboard | ✅ | `GET /admin/stats`, `GET /admin/users`, `PATCH /users/{id}/deactivate` |
| 11 | AI Chatbot & Communication | ✅ | `POST /chat/bot`, `POST /chat/whatsapp` |
| 12 | Priyo Workshop & Instant Booking | ✅ | `POST /priyo/subscribe`, `POST /priyo/instant-book`, `DELETE /priyo/unsubscribe` |
| 13 | Final Polish | ✅ | Exception handler, request logger, pagination utility, response wrappers |

## Commands run (reproducible)

```powershell
# Start server (use your local venv path)
C:\meramothub\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Run seed script (creates admin, area_manager, categories, items)
C:\meramothub\.venv\Scripts\python.exe seed_services.py

# Verify all imports compile
C:\meramothub\.venv\Scripts\python.exe -c "from app.models import *; from app.schemas import *; print('OK')"
```

## Project structure (final)

```
app/
├── __init__.py
├── config.py                    # Settings from .env
├── database.py                  # SQLAlchemy engine, Base, get_db
├── main.py                      # FastAPI app, 10 routers, 2 middleware
├── middleware/
│   ├── __init__.py
│   ├── exception_handler.py     # Global exception → JSON
│   └── request_logger.py        # Method + path + status + latency
├── models/
│   ├── __init__.py              # Exports all models
│   ├── user.py                  # User, UserRole
│   ├── service_provider.py      # ServiceProviderProfile, SkillCategory
│   ├── service.py               # ServiceCategory, ServiceItem
│   ├── booking.py               # Booking, BookingType, BookingStatus
│   ├── payment.py               # Payment, PaymentStatus
│   ├── review.py                # Review (1-5 stars + comment)
│   ├── complaint.py             # Complaint, ComplaintStatus, Resolution
│   └── subscription.py          # Subscription (Priyo Workshop)
├── routers/
│   ├── __init__.py
│   ├── auth.py                  # /auth/*
│   ├── service_providers.py     # /providers/* (incl. geo search)
│   ├── services.py              # /services/*
│   ├── bookings.py              # /bookings/*
│   ├── payments.py              # /payments/*
│   ├── reviews.py               # /reviews/*
│   ├── complaints.py            # /complaints/*
│   ├── admin.py                 # /admin/*
│   ├── chatbot.py               # /chat/*
│   └── priyo.py                 # /priyo/*
├── schemas/
│   ├── __init__.py              # Exports all schemas
│   ├── user.py
│   ├── service_provider.py      # Includes LocationUpdateSchema
│   ├── service.py
│   ├── booking.py
│   ├── payment.py
│   ├── review.py
│   ├── complaint.py
│   ├── subscription.py          # Includes InstantBookingCreateSchema
│   └── response.py              # SuccessResponse, ErrorResponse wrappers
├── services/
│   ├── __init__.py
│   ├── geo.py                   # haversine_distance()
│   ├── payment_service.py       # release_payment(), refund_payment()
│   └── chatbot_service.py       # Placeholder AI chatbot
└── utils/
    ├── __init__.py
    ├── auth.py                  # hash, verify, JWT, get_current_user
    ├── roles.py                 # require_role() dependency
    ├── pagination.py            # PaginationParams, paginate()
    ├── rate_limiter.py          # In-memory sliding window limiter
    └── whatsapp.py              # WhatsApp wa.me URL generator
```

## Swagger testing checklist

- Register → Login → Authorize (paste JWT) → test protected endpoints.
- Test provider verification flow (area_manager role required).
- Test booking lifecycle with payments and release/refund logic.
- Test geo search: update provider location → search nearby.
- Test review flow: complete booking → submit review → check rating update.
- Test complaint flow: file → assign → resolve (with refund).
- Test admin stats and user management.
- Test chatbot and WhatsApp URL generation.
- Test Priyo subscription and instant booking.

## Seeded test accounts

| User | Phone | Password | Role |
|------|-------|----------|------|
| MeramotHub Admin | 01700000001 | admin123 | admin |
| Dhaka Area Manager | 01700000002 | manager123 | area_manager |

## Notes & Recommendations

- Backup `.env` secrets before committing. Remove `SUPABASE_KEY` publishable keys from public repos.
- The seed script is idempotent — safe to run multiple times.
- Add unit tests for `auth`, `payments`, and `geo` utilities.
- Initialize Alembic for production migration management.
- The chatbot uses placeholder keyword-matching — swap in OpenAI/Anthropic API calls when ready.

---

## What's remaining

- **Alembic Migrations:** Run `alembic init alembic`, configure `env.py`, generate initial migration.
- **Frontend:** Build the React/Next.js frontend to consume all these endpoints.
