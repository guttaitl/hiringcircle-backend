"""
Authentication service for user management.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import logging

from models import User, VerificationToken, PasswordResetToken
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_verification_token,
    generate_password_reset_token
)
from services.email_service import get_email_service

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.db.query(User).filter(User.email == email.lower()).first()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def create_user(
        self,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Tuple[User, str]:
        """
        Create a new user with verification token.
        
        Returns:
            Tuple of (User, verification_token)
        """
        # Check if user already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        # Create user
        hashed_password = get_password_hash(password)
        user = User(
            email=email.lower(),
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            is_verified=False,
            is_active=True
        )
        
        self.db.add(user)
        self.db.flush()  # Get user ID without committing
        
        # Create verification token
        token = generate_verification_token()
        verification = VerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(verification)
        self.db.commit()
        
        logger.info(f"Created user: {email}")
        return user, token
    
    def verify_email(self, token: str) -> Optional[User]:
        """
        Verify user email with token.
        
        Returns:
            User if verified successfully, None otherwise
        """
        verification = self.db.query(VerificationToken).filter(
            VerificationToken.token == token
        ).first()
        
        if not verification:
            logger.warning(f"Verification token not found: {token}")
            return None
        
        if not verification.is_valid():
            logger.warning(f"Invalid or expired verification token: {token}")
            return None
        
        # Get user and mark as verified
        user = self.db.query(User).filter(User.id == verification.user_id).first()
        if not user:
            return None
        
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        
        # Mark token as used
        verification.is_used = True
        verification.used_at = datetime.utcnow()
        
        self.db.commit()
        
        # Send welcome email
        self.email_service.send_welcome_email(
            user.email,
            user.first_name or "there"
        )
        
        logger.info(f"Email verified for user: {user.email}")
        return user
    
    def resend_verification_email(self, email: str) -> bool:
        """Resend verification email to user."""
        user = self.get_user_by_email(email)
        
        if not user:
            # Don't reveal if email exists
            return True
        
        if user.is_verified:
            return True
        
        # Invalidate old tokens
        self.db.query(VerificationToken).filter(
            VerificationToken.user_id == user.id,
            VerificationToken.is_used == False
        ).update({"is_used": True})
        
        # Create new token
        token = generate_verification_token()
        verification = VerificationToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        self.db.add(verification)
        self.db.commit()
        
        # Send email
        self.email_service.send_verification_email(
            user.email,
            user.first_name or "there",
            token
        )
        
        logger.info(f"Resent verification email to: {email}")
        return True
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Returns:
            User if authentication successful, None otherwise
        """
        user = self.get_user_by_email(email)
        
        if not user:
            return None
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update login info
        user.last_login_at = datetime.utcnow()
        user.login_count += 1
        self.db.commit()
        
        logger.info(f"User authenticated: {email}")
        return user
    
    def create_tokens(self, user: User) -> dict:
        """Create access and refresh tokens for user."""
        token_data = {
            "sub": user.id,
            "email": user.email,
            "is_verified": user.is_verified
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 1800  # 30 minutes
        }
    
    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh access token using refresh token."""
        payload = verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        user = self.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        return self.create_tokens(user)
    
    def request_password_reset(self, email: str) -> bool:
        """Request password reset for user."""
        user = self.get_user_by_email(email)
        
        if not user:
            # Don't reveal if email exists
            return True
        
        # Invalidate old tokens
        self.db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False
        ).update({"is_used": True})
        
        # Create new token
        token = generate_password_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        self.db.add(reset_token)
        self.db.commit()
        
        # Send email
        self.email_service.send_password_reset_email(
            user.email,
            user.first_name or "there",
            token
        )
        
        logger.info(f"Password reset requested for: {email}")
        return True
    
    def reset_password(self, token: str, new_password: str) -> Optional[User]:
        """Reset password with token."""
        reset_token = self.db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()
        
        if not reset_token:
            logger.warning(f"Password reset token not found: {token}")
            return None
        
        if not reset_token.is_valid():
            logger.warning(f"Invalid or expired password reset token: {token}")
            return None
        
        # Get user and update password
        user = self.db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return None
        
        user.hashed_password = get_password_hash(new_password)
        user.password_reset_at = datetime.utcnow()
        
        # Mark token as used
        reset_token.is_used = True
        reset_token.used_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Password reset for user: {user.email}")
        return user
    
    def update_user(self, user: User, **kwargs) -> User:
        """Update user fields."""
        allowed_fields = ['first_name', 'last_name', 'phone', 'company', 'job_title']
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
        
        self.db.commit()
        return user
    
    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """Change user password."""
        if not verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        return True


def get_auth_service(db: Session) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)
