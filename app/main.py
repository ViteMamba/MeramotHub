import os
from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.auth import router as auth_router
from app.routers.service_providers import router as providers_router
from app.routers.services import router as services_router
from app.routers.bookings import router as bookings_router
from app.routers.payments import router as payments_router
from app.routers.reviews import router as reviews_router
from app.routers.complaints import router as complaints_router
from app.routers.admin import router as admin_router
from app.routers.chatbot import router as chatbot_router
from app.routers.priyo import router as priyo_router

# Import all models so SQLAlchemy registers their metadata
from app.models import *  # noqa: F401, F403
from app.database import engine, Base

# Middleware imports
from app.middleware.exception_handler import GlobalExceptionMiddleware
from app.middleware.request_logger import RequestLoggingMiddleware

app = FastAPI(
    title="MeramotHub API",
    description="Local service booking system connecting service providers with customers in Bangladesh.",
    version="1.0.0",
)

# Middleware stack (order matters — outermost first)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(GlobalExceptionMiddleware)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup if they don't exist (safe — won't alter existing tables)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Add missing columns to existing subscriptions table (dev migration)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS mfs_transaction_id VARCHAR(100)"))
            conn.commit()
    except Exception:
        pass  # Table might not exist yet

# Mount routers
app.include_router(auth_router)
app.include_router(providers_router)
app.include_router(services_router)
app.include_router(bookings_router)
app.include_router(payments_router)
app.include_router(reviews_router)
app.include_router(complaints_router)
app.include_router(admin_router)
app.include_router(chatbot_router)
app.include_router(priyo_router)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "nid"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to MeramotHub API 🛠️",
        "docs": "/docs",
        "version": "1.0.0",
    }
