"""
Application configuration settings.
Loads from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "HiringCircle API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    ENV: str = "production"  # Alias for ENVIRONMENT
    
    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Database - Railway PostgreSQL
    DATABASE_URL: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    JWT_SECRET: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email Configuration - SMTP
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")

    SMTP_FROM_EMAIL: Optional[str] = os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM")

    SMTP_FROM_NAME: str = "HiringCircle"

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_TIMEOUT: int = 20
    SMTP_RETRIES: int = 3
        
    # Default Email Recipients
    DEFAULT_TO_EMAIL: Optional[str] = None
    DEFAULT_BCC_EMAIL: Optional[str] = None
    
    # Frontend URL for email links
    FRONTEND_URL: str = "https://hiringcircle.us"
    VERIFICATION_CALLBACK_URL: str = "https://hiringcircle.us/verify-email"
    PASSWORD_RESET_CALLBACK_URL: str = "https://hiringcircle.us/reset-password"
    
    # CORS - Vercel frontend
    CORS_ORIGINS: str = "https://hiringcircle.us,https://www.hiringcircle.us"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    CORS_ALLOW_HEADERS: str = "*,Content-Type,Authorization,X-Requested-With"
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_FILE_SIZE_MB: int = 5
    ALLOWED_EXTENSIONS: str = "pdf,doc,docx,txt"
    UPLOAD_DIR: str = "uploads"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from environment
    
    @property
    def database_url(self) -> str:
        """Get database URL with fallback to individual components."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # Build from Railway PostgreSQL variables
        if all([self.POSTGRES_USER, self.POSTGRES_PASSWORD, self.POSTGRES_HOST, self.POSTGRES_DB]):
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
        # Fallback for local development
        return "postgresql://postgres:postgres@localhost:5432/hiringcircle"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        origins = self.CORS_ORIGINS.split(",")
        # Also add Vercel preview deployments
        origins.extend([
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:4173",
        ])
        return [origin.strip() for origin in origins if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def email_configured(self) -> bool:
        """Check if email is properly configured."""
        return all([
            self.SMTP_USERNAME,
            self.SMTP_PASSWORD,
            self.SMTP_FROM_EMAIL
        ])


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
