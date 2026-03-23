# ==========================================================
# ENVIRONMENT SETUP
# ==========================================================

import os
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)
print("🔥 FASTAPI STARTING...")

# Load .env ONLY for local (Railway already provides env vars)
if os.getenv("RAILWAY_ENVIRONMENT") is None:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is missing")

if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY missing (AI features disabled)")

if not JWT_SECRET:
    print("⚠️ JWT_SECRET missing (auth may fail)")
    
print("✅ Environment loaded")


# ==========================================================
# IMPORTS
# ==========================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.app import lifespan

# Routers
from routers.verify import router as verify_router
from api.auth_routes import router as auth_router
from api.routes.job_routes import router as job_router
from api.routes.resume_routes import router as resume_router
from api.routes.ai_match_routes import router as ai_match_router
from api.routes.employer_routes import router as employer_router

# DB
from api.db import engine, SessionLocal
from api.models import Base
import api.models  # REQUIRED

# ==========================================================
# APP INIT
# ==========================================================

app = FastAPI(
    title="Hiring Circle API",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================================
# 🚨 CORS (FIXED - NO DUPLICATE APP)
# ==========================================================

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://hiringcircleusa.vercel.app",     # ✅ NO TRAILING SPACE
    "https://hiringcircle.us",                # ✅ NO TRAILING SPACE
    "https://www.hiringcircle.us",            # ✅ NO TRAILING SPACE
    "https://hiringcircleusa-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # 🔥 CHANGE THIS
    allow_headers=["*"],
)

@app.options("/{full_path:path}")
async def options_handler():
    return {"status": "ok"}

# ==========================================================
# ROUTES
# ==========================================================

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(verify_router, prefix="/api", tags=["verify"])
app.include_router(job_router, prefix="/api", tags=["jobs"])
app.include_router(resume_router, prefix="/api", tags=["resume"])
app.include_router(ai_match_router, prefix="/api", tags=["ai"])
app.include_router(employer_router, prefix="/api", tags=["employer"])

# Health check
@app.get("/health")
def health():
    return {"status": "ok", "service": "hiring-circle-api"}
# ==========================================================
# STATIC FILES
# ==========================================================

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ==========================================================
# DATABASE INIT
# ==========================================================

@app.on_event("startup")
def startup():
    print("🚀 Starting application...")

    # Create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables ensured")
    except Exception as e:
        print("❌ Table creation failed:", e)

    # Optional: test DB connection
    try:
        with engine.connect() as conn:
            print("✅ Database connected")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():
    return {"message": "Hiring Circle API running"}

# ==========================================================
# DEBUG WORKER STATUS
# ==========================================================

@app.get("/api/workers/status")
def worker_status():
    from api.app import worker_threads, shutdown_event
    from api.core.startup_stats import startup_stats

    return {
        "shutdown_requested": shutdown_event.is_set(),
        "workers": [
            {"name": t.name, "alive": t.is_alive()}
            for t in worker_threads
        ],
        "startup_stats": dict(startup_stats)
    }