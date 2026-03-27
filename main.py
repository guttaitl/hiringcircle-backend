# ==========================================================
# ENVIRONMENT SETUP
# ==========================================================

import os
from dotenv import load_dotenv
import logging
import threading

logging.basicConfig(level=logging.INFO)
print("🔥 FASTAPI STARTING...")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

if os.getenv("RAILWAY_ENVIRONMENT") is None:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is missing")

if not OPENAI_API_KEY:
    print("⚠️ OPENAI_API_KEY missing")

if not JWT_SECRET:
    print("⚠️ JWT_SECRET missing")

print("✅ Environment loaded")


# ==========================================================
# IMPORTS
# ==========================================================
from api.routes.job_routes import router as job_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers.verify import router as verify_router
from api.auth_routes import router as auth_router
from api.routes.job_routes import router as job_router
from api.routes.resume_routes import router as resume_router
from api.routes.ai_match_routes import router as ai_match_router
from api.routes.employer_routes import router as employer_router
from api.routes.distribute_routes import router as distribute_router
from api.db import engine
from api.models import Base
from api.linkedin_routes import router as linkedin_router


# ==========================================================
# APP INIT
# ==========================================================

app = FastAPI(
    title="Hiring Circle API",
    version="1.0.0"
)


# ==========================================================
# CORS
# ==========================================================

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://hiringcircleusa.vercel.app",
    "https://hiringcircle.us",
    "https://www.hiringcircle.us",
    "https://hiringcircleusa-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
# ROUTES
# ==========================================================

app.include_router(auth_router, prefix="/api")
app.include_router(verify_router, prefix="/api")
app.include_router(job_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(ai_match_router, prefix="/api")
app.include_router(employer_router, prefix="/api")
app.include_router(distribute_router, prefix="/api")
app.include_router(linkedin_router, prefix="/api")

for route in app.routes:
    print("ROUTE:", route.path)

# ==========================================================
# HEALTH
# ==========================================================

@app.get("/health")
def health():
    return {"status": "ok"}


# ==========================================================
# STATIC FILES
# ==========================================================

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# ==========================================================
# 🚀 SAFE STARTUP (NON-BLOCKING)
# ==========================================================

@app.on_event("startup")
def startup():
    print("🚀 Starting application...")

    # DB init
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables ensured")

        with engine.connect():
            print("✅ Database connected")

    except Exception as e:
        raise RuntimeError(f"Database error: {e}")

    # 🔥 START WORKERS IN BACKGROUND (NON-BLOCKING)
    def start_background_tasks():
        try:
            print("🚀 Starting background workers...")

            from api.workers.system_warmup import warmup_resume_index
            from api.workers.job_matching_worker import run_job_matching_parallel

            # Run warmup (safe)
            threading.Thread(
                target=warmup_resume_index,
                daemon=True
            ).start()

            # Run worker
            threading.Thread(
                target=run_job_matching_parallel,
                daemon=True
            ).start()

            print("✅ Background workers started")

        except Exception as e:
            print("❌ Worker startup failed:", e)

    threading.Thread(target=start_background_tasks, daemon=True).start()


# ==========================================================
# ROOT
# ==========================================================

@app.get("/")
def root():
    return {"message": "Hiring Circle API running"}