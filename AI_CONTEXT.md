# MeramotHub - Project Context for AI Assistants

## 1. What the Project is About
**MeramotHub** is a local service booking system connecting service providers (like mechanics, electricians, cleaners, etc.) with customers in Bangladesh.
The platform allows customers to browse services, book professionals, and manage payments securely. It supports different user roles, including `Customer`, `Service Provider`, `Area Manager`, and `Admin`.

**Current Tech Stack:**
- **Backend:** Python, FastAPI, SQLAlchemy (ORM), Alembic (migrations), Pydantic (data validation).
- **Database:** PostgreSQL (hosted on Supabase).
- **Authentication:** JWT (JSON Web Tokens).

## 2. What We Did So Far
We have successfully bootstrapped the backend and implemented the core foundational modules:

- **Environment & Database:** Connected to Supabase PostgreSQL. Configured `DATABASE_URL` and JWT secrets via `.env`.
- **Authentication:** User registration (`/auth/register`), login (`/auth/login`), and JWT-based current user retrieval (`/auth/me`).
- **Service Providers:** Models, schemas, and router endpoints for service provider profiles, including a verification flow (requiring the `area_manager` role).
- **Service Catalogue:** Models and endpoints for `ServiceCategory` and `ServiceItem`. Admin-protected routes to manage the catalogue.
- **Bookings:** `Booking` models and endpoints for creating, accepting, starting, completing, and canceling bookings. The `total_price` logic securely copies the item's base price.
- **Escrow Payments:** `Payment` model with commission logic. Endpoints for holding funds, releasing to providers, processing refunds, and tracking provider earnings. Connected the `release_payment` hook to the booking completion logic.

## 3. What We Need To Do Later
The following modules and features remain to be implemented (based on the original specification roadmap):

- **Geo Search & Availability:** Add `current_latitude`, `current_longitude`, and `is_available` to the provider profile. Implement Haversine distance logic for location-based search (`app/services/geo.py`).
- **Ratings & Reviews:** Add the `Review` model. Implement logic to recompute the provider's `rating_avg` and `rating_count` when new reviews are posted.
- **Complaint System:** Implement models and endpoints to file, assign (to area managers), and resolve complaints, integrating with the payment system for refunds.
- **Admin & Area Manager Dashboards:** Build aggregation endpoints for statistics, system monitoring, and administrative actions.
- **AI Chatbot & Real-time Chat:** Integrate an AI service (OpenAI/Anthropic) for an automated chatbot, implement rate-limiting, and add WhatsApp redirect logic.
- **Priyo Workshop & Instant Booking:** Implement a subscription model (`require_pro`) and instant booking flows with auto-assignment.
- **Final Polish:** Add global exception handlers, centralized logging middleware, pagination utilities, and standardize response schemas. Finalize Alembic migrations and create seed scripts.
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
