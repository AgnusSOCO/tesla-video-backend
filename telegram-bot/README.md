# Tesla Video Player - Telegram Bot

This bot handles user authentication and YouTube video downloads for the Tesla Video Player web application.

## Setup Instructions

### 1. Create Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Save the bot token provided by BotFather

### 2. Install Dependencies

```bash
cd telegram-bot
pip3 install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file or set environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export DATABASE_URL="mysql://user:pass@host:port/database"
export WEB_APP_URL="https://your-app.manus.space"
export DOWNLOAD_PATH="/tmp/tesla-videos"
```

### 4. Run the Bot

```bash
python3 bot.py
```

Or run as a background service:

```bash
nohup python3 bot.py > bot.log 2>&1 &
```

## Features

- **QR Code Authentication**: Users scan QR code in Tesla browser to link Telegram account
- **YouTube Downloads**: Accepts YouTube URLs and downloads videos using yt-dlp
- **Progress Updates**: Real-time download status updates
- **Video Library**: List downloaded videos with `/list` command
- **Error Handling**: Graceful error handling with user-friendly messages

## Commands

- `/start` - Welcome message and instructions
- `/help` - Detailed help and usage guide
- `/auth <token>` - Link Telegram account (automatic via QR code)
- `/list` - Show downloaded videos

## Architecture

The bot interacts with the main web application database to:

1. Verify authentication tokens from QR code scans
2. Create user accounts linked to Telegram IDs
3. Store video metadata and download status
4. Track download queue and progress

Videos are downloaded using yt-dlp and stored locally (or uploaded to S3 in production).

## Production Deployment

For production use:

1. Use a process manager like `systemd` or `supervisor`
2. Configure S3 storage for video files
3. Set up proper logging and monitoring
4. Use environment variables for all configuration
5. Enable error notifications

## Troubleshooting

**Bot doesn't respond:**
- Check that TELEGRAM_BOT_TOKEN is correct
- Verify bot is running: `ps aux | grep bot.py`
- Check logs: `tail -f bot.log`

**Database connection errors:**
- Verify DATABASE_URL format and credentials
- Check database is accessible from bot server
- Ensure database schema is up to date

**Download failures:**
- Check yt-dlp is installed: `yt-dlp --version`
- Verify DOWNLOAD_PATH directory exists and is writable
- Check internet connectivity
- Some videos may be restricted or unavailable
