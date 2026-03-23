"""
User management router for profile operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from database import get_db
from schemas import UserUpdate, UserResponse, PasswordChange
from services import get_auth_service
from utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])
security = HTTPBearer()


@router.get("/me", response_model=dict)
async def get_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current user profile.
    """
    user = get_current_user(credentials.credentials, db)
    
    return {
        "success": True,
        "data": user.to_dict()
    }


@router.put("/me", response_model=dict)
async def update_profile(
    request: UserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update current user profile.
    """
    user = get_current_user(credentials.credentials, db)
    auth_service = get_auth_service(db)
    
    updated_user = auth_service.update_user(
        user,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        company=request.company,
        job_title=request.job_title
    )
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": updated_user.to_dict()
    }


@router.post("/me/change-password", response_model=dict)
async def change_password(
    request: PasswordChange,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Change current user password.
    """
    user = get_current_user(credentials.credentials, db)
    auth_service = get_auth_service(db)
    
    success = auth_service.change_password(
        user,
        request.current_password,
        request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    return {
        "success": True,
        "message": "Password changed successfully"
    }


@router.delete("/me", response_model=dict)
async def delete_account(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Delete current user account (soft delete by deactivating).
    """
    user = get_current_user(credentials.credentials, db)
    
    # Soft delete - deactivate account
    user.is_active = False
    db.commit()
    
    logger.info(f"User account deactivated: {user.email}")
    
    return {
        "success": True,
        "message": "Account deleted successfully"
    }
