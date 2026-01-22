"""
Video file upload handler for direct MP4 uploads
Converts videos to WebM format for Tesla browser compatibility
"""
import os
import logging
import subprocess
import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from s3_upload import upload_to_s3

logger = logging.getLogger(__name__)


def convert_to_webm(input_path: str, output_path: str) -> bool:
    """
    Convert video to WebM format (VP8 video, Opus audio) for Tesla browser compatibility.
    
    Tesla browser supports WebM/VP8 natively but NOT H.264/MP4.
    This conversion enables smooth video playback on Tesla while driving.
    
    Args:
        input_path: Path to input video file (MP4, etc.)
        output_path: Path for output WebM file
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        # FFmpeg command for WebM conversion
        # -c:v libvpx: VP8 video codec (Tesla browser compatible)
        # -crf 30: Constant Rate Factor (lower = better quality, 30 is good balance)
        # -b:v 1M: Target video bitrate
        # -c:a libopus: Opus audio codec (modern, efficient)
        # -b:a 128k: Audio bitrate
        # -vf scale=-1:720: Scale to 720p height, maintain aspect ratio
        # -threads 4: Use 4 threads for faster encoding
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libvpx',
            '-crf', '30',
            '-b:v', '1M',
            '-c:a', 'libopus',
            '-b:a', '128k',
            '-vf', 'scale=-1:720',
            '-threads', '4',
            '-y',  # Overwrite output file if exists
            output_path
        ]
        
        logger.info(f"Starting WebM conversion: {input_path} -> {output_path}")
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {result.stderr}")
            return False
            
        # Verify output file exists and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"WebM conversion successful: {output_path}")
            return True
        else:
            logger.error("WebM conversion produced empty or missing file")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg conversion timed out after 10 minutes")
        return False
    except Exception as e:
        logger.error(f"WebM conversion error: {e}")
        return False


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
        
        # Get video metadata
        title = file_name.rsplit('.', 1)[0]  # Remove extension
        duration = video.duration if hasattr(video, 'duration') else 0
        
        # Convert to WebM format for Tesla browser compatibility
        await status_message.edit_text(
            "🔄 Converting video for Tesla...\n\n"
            "This may take a few minutes depending on video length.\n"
            "Converting to WebM format (VP8/Opus) for smooth playback."
        )
        
        # Generate WebM filename
        webm_file_name = title + ".webm"
        webm_local_path = os.path.join(DOWNLOAD_PATH, webm_file_name)
        
        # Run conversion in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        conversion_success = await loop.run_in_executor(
            None, 
            convert_to_webm, 
            local_path, 
            webm_local_path
        )
        
        if not conversion_success:
            # Clean up original file
            if os.path.exists(local_path):
                os.remove(local_path)
            await update.message.reply_text(
                "❌ **Conversion Failed**\n\n"
                "Failed to convert video to Tesla-compatible format.\n"
                "Please try a different video or contact support."
            )
            cursor.close()
            conn.close()
            return
        
        # Delete original MP4 file after successful conversion
        if os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"Deleted original file: {local_path}")
        
        # Get WebM file size
        file_size = os.path.getsize(webm_local_path)
        
        # Upload WebM to S3 storage
        await status_message.edit_text(
            f"☁️ Uploading to cloud storage...\n\n"
            f"Size: {file_size / (1024*1024):.1f}MB (WebM)"
        )
        
        file_key = f"videos/{user_id}/{webm_file_name}"
        try:
            file_url = upload_to_s3(webm_local_path, file_key)
            logger.info(f"WebM video uploaded to S3: {file_url}")
            
            # Delete local WebM file after successful upload
            os.remove(webm_local_path)
            logger.info(f"Deleted local WebM file: {webm_local_path}")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            # Fallback to local streaming if S3 fails
            file_url = f"/api/videos/stream/{webm_file_name}"
            logger.warning(f"Using local streaming as fallback: {file_url}")
        
        # Create video record with WebM mime type
        cursor.execute(
            """INSERT INTO videos 
               (user_id, title, duration, file_key, file_url, file_size, mime_type, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (user_id, title, duration, file_key, file_url, file_size, "video/webm", "ready")
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
