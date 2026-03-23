# HiringCircle API - Deployment Guide

## Overview
This guide covers deploying the HiringCircle FastAPI backend to Railway with PostgreSQL database.

## Prerequisites
- Railway account (https://railway.app)
- GitHub account for code repository
- Gmail account for SMTP (or other email provider)

## Step 1: Push Code to GitHub

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Production-ready FastAPI backend"

# Add remote (replace with your repo)
git remote add origin https://github.com/yourusername/hiringcircle-backend.git

# Push
git push -u origin main
```

## Step 2: Deploy to Railway

### Option A: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

### Option B: Railway Dashboard (Recommended)

1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect the configuration

## Step 3: Add PostgreSQL Database

1. In Railway dashboard, click "New" → "Database" → "Add PostgreSQL"
2. Railway will automatically:
   - Create the database
   - Set environment variables (`DATABASE_URL`, `POSTGRES_*`)
   - Connect to your service

## Step 4: Configure Environment Variables

In Railway dashboard, go to your service → "Variables" tab, add:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Random 32+ character string | `your-random-secret-key-here-min-32-chars` |
| `SMTP_USERNAME` | Gmail address | `yourapp@gmail.com` |
| `SMTP_PASSWORD` | Gmail App Password | `abcd efgh ijkl mnop` |
| `SMTP_FROM_EMAIL` | Sender email | `noreply@hiringcircle.us` |
| `FRONTEND_URL` | Your Vercel frontend | `https://hiringcircle.us` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Environment name |
| `DEBUG` | `false` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |

## Step 5: Configure Gmail SMTP

1. Go to https://myaccount.google.com/
2. Enable 2-Factor Authentication
3. Go to https://myaccount.google.com/apppasswords
4. Generate App Password for "Mail"
5. Copy the 16-character password
6. Add to Railway as `SMTP_PASSWORD`

## Step 6: Verify Deployment

1. Check health endpoint:
   ```
   https://your-app.up.railway.app/health
   ```
   Should return: `{"status": "healthy", ...}`

2. Check API docs (if DEBUG=true):
   ```
   https://your-app.up.railway.app/docs
   ```

## Step 7: Connect Frontend (Vercel)

1. In Vercel dashboard, add environment variable:
   - Name: `VITE_API_URL`
   - Value: `https://your-app.up.railway.app/api/v1`

2. Redeploy frontend

## Step 8: Configure Custom Domain (GoDaddy)

### Backend (Railway)
1. In Railway dashboard → Settings → Domains
2. Click "Generate Domain" or "Custom Domain"
3. Add `api.hiringcircle.us` as custom domain
4. Copy the CNAME record

### DNS Configuration (GoDaddy)
1. Go to https://dcc.godaddy.com/manage/hiringcircle.us/dns
2. Add CNAME record:
   - Name: `api`
   - Value: (Railway CNAME)
   - TTL: 600

3. Wait for DNS propagation (5-60 minutes)

## Troubleshooting

### Database Connection Issues
```bash
# Check logs
railway logs

# Verify database URL is set
echo $DATABASE_URL
```

### Email Not Sending
1. Verify SMTP credentials
2. Check Gmail security settings
3. Review Railway logs for errors

### CORS Errors
1. Verify `CORS_ORIGINS` includes your Vercel domain
2. Check frontend is using correct API URL

### 500 Errors
1. Check `SECRET_KEY` is set
2. Verify all required env vars
3. Review application logs

## Monitoring

- Railway Dashboard: https://railway.app/dashboard
- Logs: `railway logs` or Dashboard → Logs
- Metrics: Dashboard → Metrics

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/auth/verify-email` | POST | Verify email |
| `/api/v1/auth/resend-verification` | POST | Resend verification |
| `/api/v1/auth/forgot-password` | POST | Request password reset |
| `/api/v1/auth/reset-password` | POST | Reset password |
| `/api/v1/auth/refresh` | POST | Refresh token |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/users/me` | GET | Get profile |
| `/api/v1/users/me` | PUT | Update profile |
| `/api/v1/users/me/change-password` | POST | Change password |

## Security Checklist

- [ ] `SECRET_KEY` is random and 32+ characters
- [ ] `DEBUG=false` in production
- [ ] `ENVIRONMENT=production` is set
- [ ] Gmail App Password (not regular password)
- [ ] CORS origins restricted to your domains
- [ ] Database credentials from Railway (not hardcoded)
- [ ] HTTPS enabled (Railway provides this)

## Support

For issues:
1. Check Railway logs
2. Review this guide
3. Contact support@hiringcircle.us
