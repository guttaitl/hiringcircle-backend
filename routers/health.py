"""
Health check router for monitoring and status checks.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database import get_db, check_db_connection
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.
    Used by Railway for health monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with database connectivity.
    """
    checks = {
        "api": {"status": "healthy", "response_time_ms": 0},
        "database": {"status": "unknown", "response_time_ms": 0}
    }
    
    import time
    
    # Check database
    start_time = time.time()
    db_healthy = check_db_connection()
    db_time = (time.time() - start_time) * 1000
    
    checks["database"]["status"] = "healthy" if db_healthy else "unhealthy"
    checks["database"]["response_time_ms"] = round(db_time, 2)
    
    overall_status = "healthy" if db_healthy else "degraded"
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks
    }


@router.get("/")
async def root():
    """
    API root endpoint.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs",
        "health": "/health"
    }
