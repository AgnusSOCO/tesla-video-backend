#!/usr/bin/env python3
"""
Tesla Video Player Telegram Bot
Handles authentication and YouTube video downloads
"""

import os
import sys
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
import qrcode
from io import BytesIO

import psycopg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://tesla-video-player.manus.space")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "/tmp/tesla-videos")

# Ensure download directory exists
os.makedirs(DOWNLOAD_PATH, exist_ok=True)


def get_db_connection():
    """Create database connection from DATABASE_URL"""
    # DATABASE_URL format: postgresql://user:pass@host:port/database
    # Supabase format: postgresql://postgres.PROJECT_ID:PASSWORD@HOST:PORT/postgres
    return psycopg.connect(
        DATABASE_URL,
        row_factory=psycopg.rows.dict_row
    )


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - with optional auth token from QR code"""
    user = update.effective_user
    
    # Check if auth token was provided (from QR code deep link)
    if context.args and len(context.args) == 1:
        auth_token = context.args[0]
        logger.info(f"User {user.id} scanning QR code with token: {auth_token}")
        
        # Process authentication
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if token exists and is not expired
            cursor.execute(
                "SELECT * FROM telegram_sessions WHERE authToken = %s AND expiresAt > NOW()",
                (auth_token,)
            )
            session = cursor.fetchone()
            
            if not session:
                await update.message.reply_text(
                    "❌ Invalid or expired authentication token. Please generate a new QR code from the web app."
                )
                cursor.close()
                conn.close()
                return
            
            # Check if user exists, create if not
            cursor.execute(
                "SELECT * FROM users WHERE openId = %s",
                (f"telegram_{user.id}",)
            )
            db_user = cursor.fetchone()
            
            if not db_user:
                # Create new user
                cursor.execute(
                    """INSERT INTO users (openId, name, loginMethod, role) 
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (f"telegram_{user.id}", user.full_name, "telegram", "user")
                )
                user_id = cursor.fetchone()['id']
                conn.commit()
                logger.info(f"Created new user {user_id} for Telegram user {user.id}")
            else:
                user_id = db_user['id']
                logger.info(f"Found existing user {user_id} for Telegram user {user.id}")
            
            # Update session with Telegram user info
            cursor.execute(
                """UPDATE telegram_sessions 
                   SET telegramUserId = %s, telegramUsername = %s, userId = %s, verified = TRUE
                   WHERE authToken = %s""",
                (user.id, user.username, user_id, auth_token)
            )
            conn.commit()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Authentication successful for user {user.id}")
            
            await update.message.reply_text(
                f"✅ Authentication successful, {user.first_name}!\n\n"
                "You can now return to the Tesla Video Player web app. "
                "Your session is now linked to this Telegram account.\n\n"
                "📹 Send me YouTube video URLs to start downloading!"
            )
            return
            
        except Exception as e:
            logger.error(f"Auth error: {e}")
            await update.message.reply_text(
                "❌ Authentication failed. Please try again or contact support."
            )
            return
    
    # No auth token - show welcome message
    welcome_text = f"""
👋 Welcome to Tesla Video Player, {user.first_name}!

This bot allows you to download YouTube videos and watch them in your Tesla browser while driving.

🚀 **Getting Started:**
1. Open the web app in your Tesla browser: {WEB_APP_URL}
2. Scan the QR code with Telegram to authenticate
3. Send me YouTube video links to download
4. Watch your videos in the Tesla browser!

📝 **Commands:**
/start - Show this welcome message
/help - Get help and instructions
/list - List your downloaded videos

Send me any YouTube video URL to get started!
"""
    
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 **How to Use Tesla Video Player**

**Step 1: Authentication**
1. Open {WEB_APP_URL} in your Tesla browser
2. You'll see a QR code
3. Scan it with your phone's Telegram app
4. Click the link to authenticate

**Step 2: Download Videos**
1. Find a YouTube video you want to watch
2. Copy the video URL
3. Send it to this bot
4. Wait for the download to complete

**Step 3: Watch in Tesla**
1. Open the web app in your Tesla browser
2. Your videos will appear in the library
3. Click to play - works even while driving!

**Commands:**
/start - Welcome message
/help - This help message
/list - Show your downloaded videos

**Tips:**
• Videos are stored securely in your account
• You can delete videos from the web app
• The player works while driving (canvas-based)
• Touch-optimized controls for Tesla screen

Questions? Just send me a message!
""".format(WEB_APP_URL=WEB_APP_URL)
    
    await update.message.reply_text(help_text)


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /auth <token> command for linking account"""
    user = update.effective_user
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Invalid auth command. Please scan the QR code from the web app instead."
        )
        return
    
    auth_token = context.args[0]
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if token exists and is not expired
        cursor.execute(
            "SELECT * FROM telegram_sessions WHERE authToken = %s AND expiresAt > NOW()",
            (auth_token,)
        )
        session = cursor.fetchone()
        
        if not session:
            await update.message.reply_text(
                "❌ Invalid or expired authentication token. Please generate a new QR code."
            )
            cursor.close()
            conn.close()
            return
        
        # Check if user exists, create if not
        cursor.execute(
            "SELECT * FROM users WHERE openId = %s",
            (f"telegram_{user.id}",)
        )
        db_user = cursor.fetchone()
        
        if not db_user:
            # Create new user
            cursor.execute(
                """INSERT INTO users (openId, name, loginMethod, role) 
                   VALUES (%s, %s, %s, %s) RETURNING id""",
                (f"telegram_{user.id}", user.full_name, "telegram", "user")
            )
            user_id = cursor.fetchone()['id']
            conn.commit()
        else:
            user_id = db_user['id']
        
        # Update session with Telegram user info
        cursor.execute(
            """UPDATE telegram_sessions 
               SET telegramUserId = %s, telegramUsername = %s, userId = %s, verified = TRUE
               WHERE authToken = %s""",
            (user.id, user.username, user_id, auth_token)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        await update.message.reply_text(
            "✅ Authentication successful! You can now use the Tesla Video Player web app.\n\n"
            "Send me YouTube video URLs to start downloading!"
        )
        
    except Exception as e:
        logger.error(f"Auth error: {e}")
        await update.message.reply_text(
            "❌ Authentication failed. Please try again or contact support."
        )


async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command to show user's videos"""
    user = update.effective_user
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute(
            "SELECT id FROM users WHERE openId = %s",
            (f"telegram_{user.id}",)
        )
        db_user = cursor.fetchone()
        
        if not db_user:
            await update.message.reply_text(
                "❌ You need to authenticate first. Open the web app and scan the QR code."
            )
            cursor.close()
            conn.close()
            return
        
        # Get user's videos
        cursor.execute(
            """SELECT id, title, duration, status, createdAt 
               FROM videos 
               WHERE userId = %s 
               ORDER BY createdAt DESC 
               LIMIT 10""",
            (db_user['id'],)
        )
        videos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not videos:
            await update.message.reply_text(
                "📭 You don't have any videos yet.\n\n"
                "Send me a YouTube URL to download your first video!"
            )
            return
        
        # Format video list
        video_list = "📹 **Your Videos:**\n\n"
        for video in videos:
            status_emoji = "✅" if video['status'] == 'ready' else "⏳"
            duration_str = f"{video['duration'] // 60}:{video['duration'] % 60:02d}" if video['duration'] else "N/A"
            video_list += f"{status_emoji} {video['title']}\n"
            video_list += f"   Duration: {duration_str} | ID: {video['id']}\n\n"
        
        video_list += f"\n🌐 Open {WEB_APP_URL} in your Tesla to watch!"
        
        await update.message.reply_text(video_list)
        
    except Exception as e:
        logger.error(f"List videos error: {e}")
        await update.message.reply_text(
            "❌ Failed to retrieve videos. Please try again."
        )


async def handle_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle YouTube URL messages"""
    user = update.effective_user
    url = update.message.text.strip()
    
    # Extract YouTube ID
    youtube_id = extract_youtube_id(url)
    if not youtube_id:
        await update.message.reply_text(
            "❌ Invalid YouTube URL. Please send a valid YouTube video link."
        )
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID
        cursor.execute(
            "SELECT id FROM users WHERE openId = %s",
            (f"telegram_{user.id}",)
        )
        db_user = cursor.fetchone()
        
        if not db_user:
            await update.message.reply_text(
                "❌ You need to authenticate first. Open the web app and scan the QR code:\n"
                f"{WEB_APP_URL}"
            )
            cursor.close()
            conn.close()
            return
        
        user_id = db_user['id']
        
        # Check if video already exists
        cursor.execute(
            "SELECT id, status FROM videos WHERE userId = %s AND youtubeId = %s",
            (user_id, youtube_id)
        )
        existing_video = cursor.fetchone()
        
        if existing_video:
            if existing_video['status'] == 'ready':
                await update.message.reply_text(
                    "✅ You already have this video! Check your library in the web app."
                )
            else:
                await update.message.reply_text(
                    "⏳ This video is already being downloaded. Please wait..."
                )
            cursor.close()
            conn.close()
            return
        
        # Add to download queue
        cursor.execute(
            """INSERT INTO download_queue (userId, youtubeUrl, youtubeId, status)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (user_id, url, youtube_id, "pending")
        )
        queue_id = cursor.fetchone()['id']
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Send initial message
        status_message = await update.message.reply_text(
            "⏳ Starting download...\n\n"
            f"YouTube ID: {youtube_id}"
        )
        
        # Start download in background
        asyncio.create_task(
            download_video(queue_id, user_id, url, youtube_id, status_message, context)
        )
        
    except Exception as e:
        logger.error(f"Handle URL error: {e}")
        await update.message.reply_text(
            "❌ Failed to process video. Please try again."
        )


async def download_video(queue_id: int, user_id: int, url: str, youtube_id: str, 
                        status_message, context: ContextTypes.DEFAULT_TYPE):
    """Download video using yt-dlp"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update queue status
        cursor.execute(
            "UPDATE download_queue SET status = %s WHERE id = %s",
            ("processing", queue_id)
        )
        conn.commit()
        
        # Update status message
        await status_message.edit_text(
            "📥 Downloading video...\n\n"
            "This may take a few minutes depending on video length."
        )
        
        # Configure yt-dlp
        output_path = os.path.join(DOWNLOAD_PATH, f"{youtube_id}.%(ext)s")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
        }
        
        # Download video and get info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            title = info.get('title', 'Unknown Title')
            description = info.get('description', '')
            duration = info.get('duration', 0)
            thumbnail = info.get('thumbnail', '')
            
            # Get actual downloaded file
            downloaded_file = ydl.prepare_filename(info)
            file_size = os.path.getsize(downloaded_file)
        
        # TODO: Upload to S3 storage
        # For now, we'll store file path (in production, upload to S3)
        file_key = f"videos/{user_id}/{youtube_id}.mp4"
        file_url = f"/api/videos/stream/{youtube_id}"  # Temporary local streaming
        
        # Create video record
        cursor.execute(
            """INSERT INTO videos 
               (userId, youtubeId, title, description, thumbnailUrl, duration, 
                fileKey, fileUrl, fileSize, mimeType, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, youtube_id, title, description[:500] if description else None, 
             thumbnail, duration, file_key, file_url, file_size, "video/mp4", "ready")
        )
        video_id = cursor.fetchone()['id']
        conn.commit()
        
        # Update queue
        cursor.execute(
            "UPDATE download_queue SET status = %s, videoId = %s WHERE id = %s",
            ("completed", video_id, queue_id)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Update status message
        duration_str = f"{duration // 60}:{duration % 60:02d}"
        await status_message.edit_text(
            f"✅ **Download Complete!**\n\n"
            f"📹 {title}\n"
            f"⏱ Duration: {duration_str}\n\n"
            f"🚗 Open {WEB_APP_URL} in your Tesla to watch!"
        )
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        
        # Update queue with error
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE download_queue SET status = %s, errorMessage = %s WHERE id = %s",
                ("failed", str(e), queue_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except:
            pass
        
        await status_message.edit_text(
            f"❌ **Download Failed**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or contact support if the issue persists."
        )


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
        sys.exit(1)
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("auth", auth_command))
    application.add_handler(CommandHandler("list", list_videos))
    
    # Handle YouTube URLs
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r'(youtube\.com|youtu\.be)'),
            handle_youtube_url
        )
    )
    
    # Start bot
    logger.info("Tesla Video Player Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
