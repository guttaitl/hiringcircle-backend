"""
Password reset token model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base
import uuid


def generate_uuid():
    """Generate a unique UUID string."""
    return str(uuid.uuid4())


class PasswordResetToken(Base):
    """Token for password reset functionality."""
    
    __tablename__ = "password_reset_tokens"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    
    # Token status
    is_used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Expiration (tokens expire after 1 hour)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<PasswordResetToken(user_id={self.user_id}, is_used={self.is_used})>"
    
    def is_expired(self) -> bool:
        """Check if token has expired."""
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired()
