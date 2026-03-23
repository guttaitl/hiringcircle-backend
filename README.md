# HiringCircle API

Production-ready FastAPI backend for HiringCircle - a job application and resume management platform.

## Features

- **Authentication**: JWT-based auth with access & refresh tokens
- **Email Verification**: Automatic email verification on registration
- **Password Reset**: Secure password reset via email
- **PostgreSQL Database**: SQLAlchemy ORM with Railway PostgreSQL
- **Production Ready**: Gunicorn + Uvicorn workers, health checks, CORS
- **Email Service**: SMTP support with HTML templates
- **Security**: Password hashing, token validation, rate limiting ready

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **Authentication**: JWT (python-jose) + bcrypt
- **Email**: SMTP with Jinja2 templates
- **Server**: Gunicorn + Uvicorn
- **Deployment**: Railway

## Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/hiringcircle-backend.git
cd hiringcircle-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your values

# Run development server
uvicorn main:app --reload
```

### Environment Variables

```bash
# Required
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FRONTEND_URL=http://localhost:3000

# Optional (have defaults)
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

## Project Structure

```
hiringcircle-backend/
├── core/               # Core configuration & security
│   ├── config.py      # Settings management
│   └── security.py    # JWT, password hashing
├── models/            # SQLAlchemy models
│   ├── user.py
│   ├── verification_token.py
│   └── password_reset_token.py
├── schemas/           # Pydantic schemas
│   ├── user.py
│   └── auth.py
├── routers/           # API endpoints
│   ├── auth.py
│   ├── users.py
│   └── health.py
├── services/          # Business logic
│   ├── auth_service.py
│   └── email_service.py
├── templates/         # Email templates
│   └── email/
├── utils/             # Utilities
│   └── auth.py
├── main.py            # Application entry
├── database.py        # Database configuration
├── requirements.txt   # Dependencies
├── Procfile           # Railway process
├── railway.toml       # Railway config
└── runtime.txt        # Python version
```

## API Documentation

Once running, access docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login |
| `/api/v1/auth/verify-email` | POST | Verify email |
| `/api/v1/auth/forgot-password` | POST | Request password reset |
| `/api/v1/auth/reset-password` | POST | Reset password |
| `/api/v1/users/me` | GET | Get profile |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed Railway deployment instructions.

Quick deploy:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway up
```

## Email Configuration

### Gmail SMTP

1. Enable 2-Factor Authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password (not regular password)

### Other Providers

Update `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` accordingly.

## Database Migrations

```bash
# Create migration (using Alembic)
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=.
```

## License

MIT License - See LICENSE file

## Support

For support, email support@hiringcircle.us
