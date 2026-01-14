"""
File link download handler for large video files
Supports: Pixeldrain, Google Drive, Dropbox, MediaFire, Mega, GoFile, Catbox,
          Litterbox, AnonFiles, Streamtape, 1fichier, Krakenfiles, Uploadhaven,
          Filebin, Send.cm, Buzzheavier, and direct video links
"""
import os
import logging
import re
import json
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
    match = re.search(r'pixeldrain\.com/u/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None


def extract_gofile_id(url: str) -> str:
    """Extract GoFile content ID from URL"""
    match = re.search(r'gofile\.io/d/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_catbox_id(url: str) -> str:
    """Extract Catbox file ID from URL"""
    match = re.search(r'catbox\.moe/([a-zA-Z0-9]+\.[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'files\.catbox\.moe/([a-zA-Z0-9]+\.[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_litterbox_id(url: str) -> str:
    """Extract Litterbox file ID from URL"""
    match = re.search(r'litter\.catbox\.moe/([a-zA-Z0-9]+\.[a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_mediafire_id(url: str) -> str:
    """Extract MediaFire file ID from URL"""
    match = re.search(r'mediafire\.com/file/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'mediafire\.com/download/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_krakenfiles_id(url: str) -> str:
    """Extract Krakenfiles file ID from URL"""
    match = re.search(r'krakenfiles\.com/view/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_filebin_id(url: str) -> str:
    """Extract Filebin bin/file ID from URL"""
    match = re.search(r'filebin\.net/([a-zA-Z0-9]+)/([^/?]+)', url)
    if match:
        return (match.group(1), match.group(2))
    match = re.search(r'filebin\.net/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_sendcm_id(url: str) -> str:
    """Extract Send.cm file ID from URL"""
    match = re.search(r'send\.cm/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_buzzheavier_id(url: str) -> str:
    """Extract Buzzheavier file ID from URL"""
    match = re.search(r'buzzheavier\.com/f/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def extract_1fichier_id(url: str) -> str:
    """Extract 1fichier file ID from URL"""
    match = re.search(r'1fichier\.com/\?([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None


def get_download_url(url: str) -> str:
    """Convert sharing URLs to direct download URLs"""
    
    # Pixeldrain - https://pixeldrain.com/u/FILE_ID
    if 'pixeldrain.com' in url:
        file_id = extract_pixeldrain_id(url)
        if file_id:
            return f"https://pixeldrain.com/api/file/{file_id}"
    
    # Google Drive - https://drive.google.com/file/d/FILE_ID/view
    if 'drive.google.com' in url:
        file_id = extract_google_drive_id(url)
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    
    # Dropbox - https://www.dropbox.com/s/xxx/file.mp4?dl=0
    if 'dropbox.com' in url:
        return url.replace('www.dropbox.com', 'dl.dropboxusercontent.com').replace('?dl=0', '?dl=1').replace('&dl=0', '&dl=1')
    
    # Catbox - https://catbox.moe/xxx.mp4 or https://files.catbox.moe/xxx.mp4
    # files.catbox.moe URLs are already direct download links
    if 'files.catbox.moe' in url:
        return url
    if 'catbox.moe' in url and 'litter' not in url and 'files.' not in url:
        file_id = extract_catbox_id(url)
        if file_id:
            return f"https://files.catbox.moe/{file_id}"
    
    # Litterbox (temporary Catbox) - https://litter.catbox.moe/xxx.mp4
    if 'litter.catbox.moe' in url:
        file_id = extract_litterbox_id(url)
        if file_id:
            return f"https://litter.catbox.moe/{file_id}"
    
    # Filebin - https://filebin.net/BIN_ID/filename
    if 'filebin.net' in url:
        file_info = extract_filebin_id(url)
        if isinstance(file_info, tuple):
            bin_id, filename = file_info
            return f"https://filebin.net/{bin_id}/{filename}"
        elif file_info:
            return url
    
    # file.io, transfer.sh - already direct download links
    if 'file.io' in url or 'transfer.sh' in url:
        return url
    
    # For services that need special handling (GoFile, MediaFire, etc.)
    # Return the original URL - we'll handle them specially in the download function
    return url


async def get_gofile_download_url(url: str, client: httpx.AsyncClient) -> str:
    """Get direct download URL from GoFile API"""
    content_id = extract_gofile_id(url)
    if not content_id:
        return None
    
    try:
        # First get a guest account token
        token_response = await client.post("https://api.gofile.io/accounts")
        if token_response.status_code == 200:
            token_data = token_response.json()
            if token_data.get("status") == "ok":
                token = token_data["data"]["token"]
                
                # Get content info
                headers = {"Authorization": f"Bearer {token}"}
                content_response = await client.get(
                    f"https://api.gofile.io/contents/{content_id}?wt=4fd6sg89d7s6",
                    headers=headers
                )
                if content_response.status_code == 200:
                    content_data = content_response.json()
                    if content_data.get("status") == "ok":
                        contents = content_data["data"].get("children", {})
                        for file_id, file_info in contents.items():
                            if file_info.get("type") == "file":
                                return file_info.get("link")
    except Exception as e:
        logger.error(f"GoFile API error: {e}")
    
    return None


async def get_mediafire_download_url(url: str, client: httpx.AsyncClient) -> str:
    """Scrape direct download URL from MediaFire page"""
    try:
        response = await client.get(url, follow_redirects=True)
        if response.status_code == 200:
            # Look for the download button link
            match = re.search(r'href="(https://download\d*\.mediafire\.com/[^"]+)"', response.text)
            if match:
                return match.group(1)
            # Alternative pattern
            match = re.search(r'aria-label="Download file"\s+href="([^"]+)"', response.text)
            if match:
                return match.group(1)
    except Exception as e:
        logger.error(f"MediaFire scrape error: {e}")
    
    return None


async def get_krakenfiles_download_url(url: str, client: httpx.AsyncClient) -> str:
    """Get direct download URL from Krakenfiles"""
    file_id = extract_krakenfiles_id(url)
    if not file_id:
        return None
    
    try:
        response = await client.get(url, follow_redirects=True)
        if response.status_code == 200:
            # Extract the hash token from the page
            match = re.search(r'data-file-hash="([^"]+)"', response.text)
            if match:
                file_hash = match.group(1)
                # Get download link via API
                api_response = await client.post(
                    f"https://krakenfiles.com/download/{file_id}",
                    data={"hash": file_hash}
                )
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    if api_data.get("status") == "ok":
                        return api_data.get("url")
    except Exception as e:
        logger.error(f"Krakenfiles API error: {e}")
    
    return None


async def handle_file_link(update: Update, context: ContextTypes.DEFAULT_TYPE, get_db_connection, DOWNLOAD_PATH, WEB_APP_URL):
    """Handle file sharing links for large videos"""
    user = update.effective_user
    url = update.message.text.strip()
    
    # Check if it's a valid URL
    if not url.startswith(('http://', 'https://')):
        return  # Not a URL, ignore
    
    # Check if it's a known file sharing service or direct video link
    file_services = [
        'pixeldrain.com',
        'file.io',
        'transfer.sh',
        'drive.google.com',
        'dropbox.com',
        'gofile.io',
        'catbox.moe',
        'files.catbox.moe',
        'litter.catbox.moe',
        'mediafire.com',
        'krakenfiles.com',
        'filebin.net',
        'send.cm',
        'buzzheavier.com',
        '1fichier.com',
        'anonfiles.com',
        'bayfiles.com',
        'uploadhaven.com',
        'workupload.com',
        'fileditch.com',
        'mixdrop.co',
        'streamtape.com',
    ]
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.3gp']
    
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
        
        # Get direct download URL (handles simple URL conversions)
        download_url = get_download_url(url)
        logger.info(f"Initial download URL: {download_url}")
        
        # Download file
        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            # Handle services that need special API calls to get download URL
            if 'gofile.io' in url:
                logger.info("Detected GoFile link, fetching direct URL via API...")
                gofile_url = await get_gofile_download_url(url, client)
                if gofile_url:
                    download_url = gofile_url
                    logger.info(f"GoFile direct URL: {download_url}")
                else:
                    raise Exception("Could not get download URL from GoFile. The file may be private or deleted.")
            
            elif 'mediafire.com' in url:
                logger.info("Detected MediaFire link, scraping direct URL...")
                mediafire_url = await get_mediafire_download_url(url, client)
                if mediafire_url:
                    download_url = mediafire_url
                    logger.info(f"MediaFire direct URL: {download_url}")
                else:
                    raise Exception("Could not get download URL from MediaFire. The file may be private or deleted.")
            
            elif 'krakenfiles.com' in url:
                logger.info("Detected Krakenfiles link, fetching direct URL via API...")
                kraken_url = await get_krakenfiles_download_url(url, client)
                if kraken_url:
                    download_url = kraken_url
                    logger.info(f"Krakenfiles direct URL: {download_url}")
                else:
                    raise Exception("Could not get download URL from Krakenfiles. The file may be private or deleted.")
            
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
