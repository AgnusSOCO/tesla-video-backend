# Environment Variables Configuration

This document lists all environment variables needed for deploying the Tesla Video Player to Vercel, Railway, and Supabase.

## Backend (Railway)

### Required Variables

```bash
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/database

# JWT Secret for session management
JWT_SECRET=your-random-secret-key-here

# Frontend URL (Vercel deployment)
FRONTEND_URL=https://your-app.vercel.app

# Server Configuration
PORT=3000
NODE_ENV=production

# CORS Configuration
ALLOWED_ORIGINS=https://your-app.vercel.app
```

### Optional Variables (for S3 storage)

```bash
# S3 Storage (for video files)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
AWS_S3_ENDPOINT=https://s3.amazonaws.com
```

### Optional Variables (for Telegram bot on Railway)

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
DOWNLOAD_PATH=/tmp/videos
```

## Frontend (Vercel)

### Required Variables

```bash
# Backend API URL (Railway deployment)
VITE_API_URL=https://your-backend.railway.app

# App Configuration
VITE_APP_TITLE=Tesla Video Player
VITE_APP_LOGO=
```

## Telegram Bot (Separate Server)

### Required Variables

```bash
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

# Database (same as backend)
DATABASE_URL=postgresql://user:password@host:port/database

# Web App URL (Vercel frontend)
WEB_APP_URL=https://your-app.vercel.app

# Download Configuration
DOWNLOAD_PATH=/home/user/tesla-videos
```

### Optional Variables (for S3 upload)

```bash
# S3 Storage (same as backend)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name
AWS_S3_ENDPOINT=https://s3.amazonaws.com
```

## How to Get These Values

### DATABASE_URL (Supabase)
1. Go to your Supabase project dashboard
2. Click "Settings" → "Database"
3. Copy the "Connection string" under "Connection pooling"
4. Use the "Transaction" mode connection string

### JWT_SECRET
Generate a random secret:
```bash
openssl rand -base64 32
```

### TELEGRAM_BOT_TOKEN
1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow instructions
3. Copy the token provided

### AWS S3 Credentials
1. Go to AWS Console → IAM
2. Create a new user with S3 permissions
3. Generate access keys
4. Create an S3 bucket for video storage

## Setting Environment Variables

### Railway
1. Go to your Railway project
2. Click "Variables" tab
3. Add each variable with its value
4. Railway will automatically redeploy

### Vercel
1. Go to your Vercel project
2. Click "Settings" → "Environment Variables"
3. Add each variable with its value
4. Redeploy to apply changes

### Telegram Bot Server
Create a `.env` file or use systemd environment file:
```bash
# Using .env file
nano .env
# Add variables, then:
export $(cat .env | xargs)

# Or using systemd
sudo nano /etc/systemd/system/tesla-video-bot.service
# Add Environment= lines in [Service] section
```
