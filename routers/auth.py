"""
Authentication router for login, register, and token management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from database import get_db
from schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    EmailVerificationRequest,
    ResendVerificationRequest,
    RefreshTokenRequest,
    UserResponse
)
from services import get_auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    Sends verification email automatically.
    """
    auth_service = get_auth_service(db)
    
    try:
        user, token = auth_service.create_user(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name
        )
        
        # Send verification email
        from services import get_email_service
        email_service = get_email_service()
        email_sent = email_service.send_verification_email(
            user.email,
            user.first_name or "there",
            token
        )
        
        if not email_sent:
            logger.warning(f"Failed to send verification email to {user.email}")
        
        return {
            "success": True,
            "message": "Registration successful. Please check your email to verify your account.",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "email_sent": email_sent
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )


@router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns access and refresh tokens.
    """
    auth_service = get_auth_service(db)
    
    # Authenticate user
    user = auth_service.authenticate_user(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link."
        )
    
    # Create tokens
    tokens = auth_service.create_tokens(user)
    
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            **tokens,
            "user": user.to_dict()
        }
    }


@router.post("/verify-email", response_model=dict)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify email address with verification token.
    """
    auth_service = get_auth_service(db)
    
    user = auth_service.verify_email(request.token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {
        "success": True,
        "message": "Email verified successfully. You can now log in.",
        "data": {
            "email": user.email,
            "is_verified": user.is_verified
        }
    }


@router.post("/resend-verification", response_model=dict)
async def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Resend verification email.
    """
    auth_service = get_auth_service(db)
    auth_service.resend_verification_email(request.email)
    
    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If an account exists with this email, a verification link has been sent."
    }


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    """
    auth_service = get_auth_service(db)
    auth_service.request_password_reset(request.email)
    
    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If an account exists with this email, a password reset link has been sent."
    }


@router.post("/reset-password", response_model=dict)
async def reset_password(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset password with reset token.
    """
    auth_service = get_auth_service(db)
    
    user = auth_service.reset_password(request.token, request.new_password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {
        "success": True,
        "message": "Password reset successfully. You can now log in with your new password.",
        "data": {
            "email": user.email
        }
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    auth_service = get_auth_service(db)
    
    tokens = auth_service.refresh_access_token(request.refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "success": True,
        "message": "Token refreshed successfully",
        "data": tokens
    }


@router.post("/logout", response_model=dict)
async def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Logout user (invalidate token - client should also remove tokens).
    Note: JWT tokens are stateless, so we rely on client to remove them.
    For server-side invalidation, implement a token blacklist.
    """
    # TODO: Implement token blacklist for true server-side logout
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get current logged-in user information.
    """
    from utils.auth import get_current_user
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = get_current_user(credentials.credentials, db)
    
    return {
        "success": True,
        "data": user.to_dict()
    }
