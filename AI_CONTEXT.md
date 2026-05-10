# MeramotHub - Project Context for AI Assistants

## 1. What the Project is About
**MeramotHub** is a local service booking system connecting service providers (like mechanics, electricians, cleaners, etc.) with customers in Bangladesh.
The platform allows customers to browse services, book professionals, and manage payments securely. It supports different user roles, including `Customer`, `Service Provider`, `Area Manager`, and `Admin`.

**Current Tech Stack:**
- **Backend:** Python, FastAPI, SQLAlchemy (ORM), Alembic (migrations), Pydantic (data validation).
- **Database:** PostgreSQL (hosted on Supabase).
- **Authentication:** JWT (JSON Web Tokens).

## 2. What We Did So Far
We have successfully bootstrapped the backend and implemented all backend modules (Pages 1–13):

- **Environment & Database:** Connected to Supabase PostgreSQL. Configured `DATABASE_URL` and JWT secrets via `.env`.
- **Authentication:** User registration (`/auth/register`), login (`/auth/login`), and JWT-based current user retrieval (`/auth/me`).
- **Service Providers:** Models, schemas, and router endpoints for service provider profiles, including a verification flow (requiring the `area_manager` role).
- **Service Catalogue:** Models and endpoints for `ServiceCategory` and `ServiceItem`. Admin-protected routes to manage the catalogue.
- **Bookings:** `Booking` models and endpoints for creating, accepting, starting, completing, and canceling bookings. The `total_price` logic securely copies the item's base price.
- **Escrow Payments:** `Payment` model with commission logic. Endpoints for holding funds, releasing to providers, processing refunds, and tracking provider earnings. Connected the `release_payment` hook to the booking completion logic.
- **Geo Search & Availability:** `PATCH /providers/profile/location` and `GET /providers/nearby` endpoints with Haversine distance filtering. Model columns for `current_latitude`, `current_longitude`, `is_available`, `last_seen_at`.
- **Ratings & Reviews:** `Review` model with `POST /reviews/` and `GET /reviews/provider/{id}`. Automatic recomputation of `rating_avg` and `rating_count` on the provider profile.
- **Complaint System:** `Complaint` model with full workflow — file, assign (to area managers), resolve/dismiss. Integrated with `refund_payment()` for complaint resolution.
- **Admin & Area Manager Dashboards:** Platform-wide stats endpoint (`GET /admin/stats`), user management (list, deactivate, activate, change role), and area manager-specific stats.
- **AI Chatbot & Communication:** Placeholder chatbot endpoint (`POST /chat/bot`) with rate limiting (10 req/min per user) and WhatsApp URL generator (`POST /chat/whatsapp`).
- **Priyo Workshop & Instant Booking:** `Subscription` model, subscribe/unsubscribe endpoints, and instant booking with auto-assignment of nearest Priyo-subscribed provider.
- **Final Polish:** Global exception handler middleware, request logging middleware, pagination utility, standardized response schema wrappers, and expanded idempotent seed script (admin/area_manager users + 5 categories + 13 items).

## 3. What We Need To Do Later
The following remains:

- **Alembic Migrations:** Initialize Alembic (`alembic init`) and generate the initial migration from existing models.
- **Frontend Application:** Build the React/Next.js frontend application to consume the FastAPI backend endpoints.


## 4. How We Will Do It Without Breaking Any Structure
To maintain the structural integrity and codebase quality, any AI assisting in this project **must** adhere to the following rules:

1. **Follow the Existing Architecture:** 
   - Add new SQLAlchemy models to `app/models/` and ensure they are imported in `app/database.py` (or similar registry) so Alembic can detect them.
   - Add Pydantic validation schemas to `app/schemas/`. Use strict typing.
   - Add new route handlers to `app/routers/` and register the new routers in `app/main.py`.
   - Add complex business logic (like Geo calculations) to `app/services/` or `app/utils/`.

2. **Maintain Security & Dependency Injection:**
   - Always use FastAPI's `Depends(get_current_user)` or `Depends(require_role(...))` for protected routes to maintain secure access control.
   - Do not bypass password hashing or JWT validation.

3. **Database Consistency:**
   - Do not alter existing tables without carefully considering Alembic migrations. 
   - Maintain the use of UUIDs for primary keys (`UUID(as_uuid=True)`) as established in the base models.
   - When referencing other tables, use explicit Foreign Keys and SQLAlchemy relationships.

4. **Code Quality & Style:**
   - Do not remove or modify unrelated existing comments, docstrings, or imports. 
   - Avoid creating massive single files; stick to the modular separation of concerns (Models -> Schemas -> Routers -> Services).
   - Ensure CORS settings in `app/main.py` remain intact for frontend access.

5. **Safe File Modification:** 
   - When modifying files, use localized, block-specific edits rather than completely overwriting an entire file, to avoid accidental deletion of recent manual fixes.
   - Review file contents before making edits.
