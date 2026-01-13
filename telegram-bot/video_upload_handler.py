"""
Video file upload handler for direct MP4 uploads
"""
import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from s3_upload import upload_to_s3

logger = logging.getLogger(__name__)


async def handle_video_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, get_db_connection, DOWNLOAD_PATH, WEB_APP_URL):
    """Handle direct video file uploads"""
    user = update.effective_user
    video = update.message.video or update.message.document
    
    if not video:
        return
    
    # Check file size (Telegram limit is 2GB, but we might want a smaller limit)
    MAX_SIZE = 500 * 1024 * 1024  # 500MB limit
    if video.file_size > MAX_SIZE:
        await update.message.reply_text(
            f"❌ File too large! Maximum size is {MAX_SIZE // (1024*1024)}MB.\n"
            f"Your file: {video.file_size // (1024*1024)}MB"
        )
        return
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID from database
        cursor.execute(
            "SELECT id FROM users WHERE open_id = %s",
            (f"telegram_{user.id}",)
        )
        db_user = cursor.fetchone()
        
        if not db_user:
            await update.message.reply_text(
                "❌ Please authenticate first by scanning the QR code from the web app."
            )
            cursor.close()
            conn.close()
            return
        
        user_id = db_user['id']
        
        # Send initial status
        status_message = await update.message.reply_text(
            "📥 Downloading video from Telegram...\n\n"
            f"Size: {video.file_size / (1024*1024):.1f}MB"
        )
        
        # Download file from Telegram
        file = await context.bot.get_file(video.file_id)
        
        # Generate filename
        file_name = video.file_name if hasattr(video, 'file_name') and video.file_name else f"video_{video.file_id}.mp4"
        local_path = os.path.join(DOWNLOAD_PATH, file_name)
        
        # Download
        await file.download_to_drive(local_path)
        
        # Update status
        await status_message.edit_text(
            "💾 Processing video...\n\n"
            "Saving to database..."
        )
        
        # Get video metadata
        title = file_name.rsplit('.', 1)[0]  # Remove extension
        file_size = os.path.getsize(local_path)
        duration = video.duration if hasattr(video, 'duration') else 0
        
        # Upload to S3 storage
        await status_message.edit_text(
            f"☁️ Uploading to cloud storage...

"
            f"Size: {file_size / (1024*1024):.1f}MB"
        )
        
        file_key = f"videos/{user_id}/{file_name}"
        try:
            file_url = upload_to_s3(local_path, file_key)
            logger.info(f"Video uploaded to S3: {file_url}")
            
            # Delete local file after successful upload
            os.remove(local_path)
            logger.info(f"Deleted local file: {local_path}")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            # Fallback to local streaming if S3 fails
            file_url = f"/api/videos/stream/{file_name}"
            logger.warning(f"Using local streaming as fallback: {file_url}")
        
        # Create video record
        cursor.execute(
            """INSERT INTO videos 
               (user_id, title, duration, file_key, file_url, file_size, mime_type, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, title, duration, file_key, file_url, file_size, "video/mp4", "ready")
        )
        video_id = cursor.fetchone()['id']
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Success message
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else "Unknown"
        await status_message.edit_text(
            f"✅ **Upload Complete!**\n\n"
            f"📹 {title}\n"
            f"⏱ Duration: {duration_str}\n"
            f"💾 Size: {file_size / (1024*1024):.1f}MB\n\n"
            f"🚗 Open {WEB_APP_URL} in your Tesla to watch!"
        )
        
        logger.info(f"Video uploaded successfully: {title} (user {user_id})")
        
    except Exception as e:
        logger.error(f"Video upload error: {e}")
        await update.message.reply_text(
            f"❌ **Upload Failed**\n\n"
            f"Error: {str(e)}\n\n"
            "Please try again or contact support."
        )
