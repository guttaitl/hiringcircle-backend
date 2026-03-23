# HiringCircle Backend - Setup Checklist

## ✅ What Was Fixed

### 1. Railway Deployment Issues
- **Fixed**: Proper `Procfile` with Gunicorn + Uvicorn workers
- **Fixed**: `railway.toml` with health checks and deployment config
- **Fixed**: `runtime.txt` specifying Python 3.11.6
- **Fixed**: `nixpacks.toml` for proper build process
- **Fixed**: `requirements.txt` with all necessary dependencies

### 2. Email Verification Issues
- **Fixed**: Complete email service with SMTP support
- **Fixed**: HTML email templates (verification, password reset, welcome)
- **Fixed**: Token generation and validation
- **Fixed**: Gmail SMTP configuration guide
- **Fixed**: Resend verification functionality

### 3. Login Issues
- **Fixed**: JWT token creation and validation
- **Fixed**: Password hashing with bcrypt
- **Fixed**: User authentication flow
- **Fixed**: Token refresh mechanism
- **Fixed**: Protected route dependencies

### 4. Database Configuration
- **Fixed**: SQLAlchemy 2.0 models
- **Fixed**: PostgreSQL connection with Railway
- **Fixed**: Automatic table creation on startup
- **Fixed**: Connection pooling for production

### 5. CORS Configuration
- **Fixed**: CORS middleware for Vercel frontend
- **Fixed**: Proper origin allowlist
- **Fixed**: Credentials support for cookies/auth

## 📁 Project Structure

```
hiringcircle-backend/
├── core/                    # Core configuration
│   ├── config.py           # Environment settings
│   └── security.py         # JWT & password hashing
├── models/                  # Database models
│   ├── user.py
│   ├── verification_token.py
│   └── password_reset_token.py
├── routers/                 # API endpoints
│   ├── auth.py             # Login, register, verify
│   ├── users.py            # Profile management
│   └── health.py           # Health checks
├── services/                # Business logic
│   ├── auth_service.py     # Authentication logic
│   └── email_service.py    # Email sending
├── schemas/                 # Pydantic models
│   ├── user.py
│   └── auth.py
├── templates/email/         # HTML email templates
│   ├── verification.html
│   ├── password_reset.html
│   └── welcome.html
├── utils/                   # Utilities
│   └── auth.py             # Auth dependencies
├── main.py                  # Application entry
├── database.py              # Database config
├── requirements.txt         # Dependencies
├── Procfile                 # Railway process
├── railway.toml             # Railway config
├── runtime.txt              # Python version
├── .env.example             # Environment template
├── DEPLOYMENT.md            # Deployment guide
├── FRONTEND_INTEGRATION.md  # Frontend guide
└── README.md                # Project readme
```

## 🚀 Quick Deployment Steps

### Step 1: Push to GitHub
```bash
cd hiringcircle-backend
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/hiringcircle-backend.git
git push -u origin main
```

### Step 2: Deploy to Railway
1. Go to https://railway.app/dashboard
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository
4. Railway auto-deploys!

### Step 3: Add PostgreSQL
1. In Railway dashboard, click "New" → "Database" → "PostgreSQL"
2. Railway auto-connects database

### Step 4: Configure Environment Variables
In Railway dashboard → Your Service → Variables, add:

```
SECRET_KEY=your-random-secret-key-min-32-characters
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM_EMAIL=noreply@hiringcircle.us
FRONTEND_URL=https://hiringcircle.us
```

### Step 5: Configure Gmail SMTP
1. Go to https://myaccount.google.com/
2. Enable 2-Factor Authentication
3. Generate App Password: https://myaccount.google.com/apppasswords
4. Use the 16-character password as `SMTP_PASSWORD`

### Step 6: Verify Deployment
```bash
curl https://your-app.up.railway.app/health
```
Should return: `{"status": "healthy", ...}`

## 🔧 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Random 32+ char string for JWT |
| `DATABASE_URL` | ⚪ | Auto-set by Railway PostgreSQL |
| `SMTP_USERNAME` | ✅ | Gmail address |
| `SMTP_PASSWORD` | ✅ | Gmail App Password |
| `SMTP_FROM_EMAIL` | ✅ | Sender email |
| `FRONTEND_URL` | ✅ | Your Vercel domain |
| `ENVIRONMENT` | ⚪ | `production` (default) |
| `DEBUG` | ⚪ | `false` (default) |

## 🌐 Frontend Configuration

In your Vercel frontend, set:
```
VITE_API_URL=https://your-railway-app.up.railway.app/api/v1
```

For custom domain:
```
VITE_API_URL=https://api.hiringcircle.us/api/v1
```

## 📧 Email Templates

The backend includes professional HTML email templates:
- **Verification**: Sent on registration
- **Password Reset**: Sent on forgot password request
- **Welcome**: Sent after email verification

## 🔒 Security Features

- ✅ JWT authentication with access & refresh tokens
- ✅ Bcrypt password hashing
- ✅ Email verification required for login
- ✅ Secure token generation (secrets module)
- ✅ CORS configured for your domains only
- ✅ HTTPS enforcement in production
- ✅ SQL injection protection (SQLAlchemy)
- ✅ XSS protection (Jinja2 autoescape)

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check if DATABASE_URL is set
railway variables

# Test connection
python scripts/init_db.py
```

### Email Not Sending
1. Verify SMTP credentials in Railway
2. Check Gmail security settings
3. Use App Password (not regular password)
4. Check Railway logs: `railway logs`

### CORS Errors
1. Verify `CORS_ORIGINS` includes your Vercel domain
2. Check frontend is using correct API URL
3. Ensure `withCredentials: true` in Axios

### 500 Errors
1. Check `SECRET_KEY` is set (min 32 chars)
2. Verify all required env vars
3. Review Railway logs

## 📚 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/verify-email` - Verify email
- `POST /api/v1/auth/resend-verification` - Resend verification
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Users
- `GET /api/v1/users/me` - Get profile
- `PUT /api/v1/users/me` - Update profile
- `POST /api/v1/users/me/change-password` - Change password
- `DELETE /api/v1/users/me` - Delete account

### Health
- `GET /health` - Health check
- `GET /health/detailed` - Detailed health with DB status

## 🎯 Next Steps

1. ✅ Download the backend code
2. ✅ Push to your GitHub repository
3. ✅ Deploy to Railway
4. ✅ Add PostgreSQL database
5. ✅ Configure environment variables
6. ✅ Set up Gmail SMTP
7. ✅ Update frontend API URL
8. ✅ Test registration & login flow
9. ✅ Configure custom domain (optional)

## 📞 Support

For issues or questions:
1. Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
2. Check [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md) for frontend setup
3. Review Railway logs: `railway logs`
4. Contact: support@hiringcircle.us
