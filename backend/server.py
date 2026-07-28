"""
Vigil API - Price Tracking Service

FastAPI application entry point.
Routers are imported from the routes/ and auth modules.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from config import db, logger, FRONTEND_URL
from auth import router as auth_router
from routes.items import router as items_router
from cron import start_scheduler, shutdown_scheduler

# Create the main app
app = FastAPI(title="Vigil API - Price Tracking Service")

# Include routers
app.include_router(auth_router)
app.include_router(items_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== ROOT ENDPOINT ====================


@app.get("/api/")
async def root():
    return {"message": "Vigil API - Price Tracking Service"}


# ==================== LIFECYCLE ====================


@app.on_event("startup")
async def startup_event():
    """Start the scheduler on app startup."""
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler and database on app shutdown."""
    shutdown_scheduler()
    client = db.client
    client.close()