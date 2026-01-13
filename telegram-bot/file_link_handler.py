"""
File link download handler for large video files
Supports: Pixeldrain, Google Drive, Dropbox, direct links
"""
import os
import logging
import re
import httpx
from telegram import Update
from telegram.ext import ContextTypes
from s3_upload import upload_to_s3

logger = logging.getLogger(__name__)


def extract_google_drive_id(url: str) -> str:
    """Extract Google Drive file ID from various URL formats"""
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/open\?id=([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_pixeldrain_id(url: str) -> str:
    """Extract Pixeldrain file ID from URL"""
    # Format: https://pixeldrain.com/u/FILE_ID
    match = re.search(r'pixeldrain\.com/u/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None


def get_download_url(url: str) -> str:
    """Convert sharing URLs to direct download URLs"""
    # Pixeldrain
    if 'pixeldrain.com' in url:
        file_id = extract_pixeldrain_id(url)
        if file_id:
            return f"https://pixeldrain.com/api/file/{file_id}"
    
    # Google Drive - use multiple download methods
    if 'drive.google.com' in url:
        file_id = extract_google_drive_id(url)
        if file_id:
            # For large files, use the confirm parameter to bypass virus scan
            return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    
    # Dropbox
    if 'dropbox.com' in url:
        return url.replace('www.dropbox.com', 'dl.dropboxusercontent.com').replace('?dl=0', '?dl=1')
    
    # file.io, transfer.sh, and other direct links
    return url


async def handle_file_link(update: Update, context: ContextTypes.DEFAULT_TYPE, get_db_connection, DOWNLOAD_PATH, WEB_APP_URL):
    """Handle file sharing links for large videos"""
    user = update.effective_user
    url = update.message.text.strip()
    
    # Check if it's a valid URL
    if not url.startswith(('http://', 'https://')):
        return  # Not a URL, ignore
    
    # Check if it's a known file sharing service or direct video link
    file_services = ['pixeldrain.com', 'file.io', 'transfer.sh', 'drive.google.com', 'dropbox.com']
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']
    
    is_file_service = any(service in url.lower() for service in file_services)
    is_video_link = any(url.lower().endswith(ext) for ext in video_extensions)
    
    if not (is_file_service or is_video_link):
        return  # Not a file link, ignore
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user ID
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
            "📥 Downloading video from link...\n\n"
            "This may take a few minutes for large files."
        )
        
        # Get direct download URL
        download_url = get_download_url(url)
        logger.info(f"Downloading from: {download_url}")
        
        # Download file
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            # First, get file info
            try:
                head_response = await client.head(download_url)
                file_size = int(head_response.headers.get('content-length', 0))
            except:
                file_size = 0
            
            # Download the file
            response = await client.get(download_url, follow_redirects=True)
            
            # Check if Google Drive returned HTML (virus scan page)
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type and 'drive.google.com' in url:
                raise Exception(
                    "Google Drive requires manual download for this file. "
                    "Please download it manually and send the file directly to the bot, "
                    "or use Pixeldrain (https://pixeldrain.com) instead."
                )
            
            if response.status_code != 200:
                raise Exception(f"Download failed with status {response.status_code}")
            
            # Get actual file size
            if file_size == 0:
                file_size = len(response.content)
            
            # Check file size
            MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB limit
            if file_size > MAX_SIZE:
                await status_message.edit_text(
                    f"❌ File too large! Maximum size is {MAX_SIZE // (1024*1024*1024)}GB.\n"
                    f"Your file: {file_size // (1024*1024*1024):.1f}GB"
                )
                cursor.close()
                conn.close()
                return
            
            # Update status
            await status_message.edit_text(
                f"💾 Processing video...\n\n"
                f"Size: {file_size / (1024*1024):.1f}MB"
            )
            
            # Save file
            filename = url.split('/')[-1].split('?')[0]
            if not any(filename.lower().endswith(ext) for ext in video_extensions):
                filename = f"video_{user_id}_{abs(hash(url))}.mp4"
            
            local_path = os.path.join(DOWNLOAD_PATH, filename)
            
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Get video metadata
            title = filename.rsplit('.', 1)[0]
            actual_size = os.path.getsize(local_path)
            
            # Upload to S3 storage
            await status_message.edit_text(
                f"☁️ Uploading to cloud storage...\n\n"
                f"Size: {actual_size / (1024*1024):.1f}MB"
            )
            
            file_key = f"videos/{user_id}/{filename}"
            try:
                file_url = upload_to_s3(local_path, file_key)
                logger.info(f"Video uploaded to S3: {file_url}")
                
                # Delete local file after successful upload
                os.remove(local_path)
                logger.info(f"Deleted local file: {local_path}")
            except Exception as e:
                logger.error(f"S3 upload failed: {e}")
                # Fallback to local streaming if S3 fails
                file_url = f"/api/videos/stream/{filename}"
                logger.warning(f"Using local streaming as fallback: {file_url}")
            
            # Create video record (youtubeId is NULL for non-YouTube videos)
            cursor.execute(
                """INSERT INTO videos 
                   (user_id, youtube_id, title, file_key, file_url, file_size, mime_type, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (user_id, None, title, file_key, file_url, actual_size, "video/mp4", "ready")
            )
            video_id = cursor.fetchone()['id']
            conn.commit()
            
            cursor.close()
            conn.close()
            
            # Success message
            await status_message.edit_text(
                f"✅ **Download Complete!**\n\n"
                f"📹 {title}\n"
                f"💾 Size: {actual_size / (1024*1024):.1f}MB\n\n"
                f"🚗 Open {WEB_APP_URL} in your Tesla to watch!"
            )
            
            logger.info(f"Video downloaded from link: {title} (user {user_id})")
            
    except httpx.TimeoutException:
        logger.error(f"Download timeout for URL: {url}")
        await update.message.reply_text(
            "❌ **Download Timeout**\n\n"
            "The file took too long to download. Please try:\n"
            "1. A smaller file\n"
            "2. A faster hosting service\n"
            "3. Splitting the video into parts"
        )
    except Exception as e:
        logger.error(f"File link download error: {e}")
        await update.message.reply_text(
            f"❌ **Download Failed**\n\n"
            f"Error: {str(e)}\n\n"
            "Make sure the link is:\n"
            "• A direct download link\n"
            "• Publicly accessible\n"
            "• A video file"
        )
