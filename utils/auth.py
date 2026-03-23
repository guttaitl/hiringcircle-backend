"""
Authentication utilities and dependencies.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.security import verify_token
from models import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    token: str,
    db: Session
) -> User:
    """
    Get current user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token, token_type="access")
    
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current active user.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        User object
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return get_current_user(credentials.credentials, db)


def require_verified_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get verified user.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        User object (must be verified)
    """
    user = get_current_active_user(credentials, db)
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    
    return user


def optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional dependency to get current user.
    Returns None if no valid credentials provided.
    
    Args:
        credentials: HTTP Authorization credentials
        db: Database session
        
    Returns:
        User object or None
    """
    if not credentials:
        return None
    
    try:
        return get_current_user(credentials.credentials, db)
    except HTTPException:
        return None
