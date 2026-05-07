from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.auth import router as auth_router
from app.routers.service_providers import router as providers_router
from app.routers.services import router as services_router
from app.routers.bookings import router as bookings_router
from app.routers.payments import router as payments_router

app = FastAPI(
    title="MeramotHub API",
    description="Local service booking system connecting service providers with customers in Bangladesh.",
    version="1.0.0",
)

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router)
app.include_router(providers_router)
app.include_router(services_router)
app.include_router(bookings_router)
app.include_router(payments_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to MeramotHub API 🛠️",
        "docs": "/docs",
        "version": "1.0.0",
    }
