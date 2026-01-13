"""
Piped API YouTube Downloader

Uses the Piped API (privacy-friendly YouTube frontend) to download videos.
This bypasses YouTube's blocking mechanisms by using Piped's proxy infrastructure.

API Documentation: https://docs.piped.video/docs/api-documentation/
"""

import os
import logging
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# List of public Piped API instances for redundancy
# These are rotated through if one fails
PIPED_API_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
    "https://api.piped.privacydev.net",
    "https://pipedapi.r4fo.com",
    "https://pipedapi.moomoo.me",
    "https://pipedapi.syncpundit.io",
    "https://api-piped.mha.fi",
]

# Download settings
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
REQUEST_TIMEOUT = 30  # seconds for API requests
DOWNLOAD_TIMEOUT = 600  # 10 minutes for video download


@dataclass
class VideoInfo:
    """Video information from Piped API"""
    title: str
    description: str
    duration: int
    thumbnail_url: str
    uploader: str
    views: int
    video_url: str
    audio_url: Optional[str]
    is_video_only: bool
    quality: str


async def get_video_info(video_id: str, instance_url: str = None) -> Optional[VideoInfo]:
    """
    Get video information and stream URLs from Piped API
    
    Args:
        video_id: YouTube video ID
        instance_url: Specific Piped instance to use (optional)
    
    Returns:
        VideoInfo object with stream URLs, or None if failed
    """
    instances_to_try = [instance_url] if instance_url else PIPED_API_INSTANCES
    
    for instance in instances_to_try:
        try:
            logger.info(f"Trying Piped instance: {instance}")
            
            async with aiohttp.ClientSession() as session:
                url = f"{instance}/streams/{video_id}"
                
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                    if response.status != 200:
                        logger.warning(f"Piped instance {instance} returned status {response.status}")
                        continue
                    
                    data = await response.json()
                    
                    if "error" in data:
                        logger.warning(f"Piped instance {instance} returned error: {data.get('error')}")
                        continue
                    
                    # Find the best video stream (prefer combined video+audio)
                    video_streams = data.get("videoStreams", [])
                    audio_streams = data.get("audioStreams", [])
                    
                    if not video_streams:
                        logger.warning(f"No video streams found from {instance}")
                        continue
                    
                    # Sort video streams by quality (prefer 720p or 1080p)
                    # Filter for MP4 format which is most compatible
                    mp4_streams = [s for s in video_streams if s.get("mimeType", "").startswith("video/mp4")]
                    
                    if not mp4_streams:
                        # Fall back to any video stream
                        mp4_streams = video_streams
                    
                    # Sort by height (resolution) - prefer 720p for balance of quality and size
                    def get_stream_priority(stream):
                        height = stream.get("height", 0)
                        video_only = stream.get("videoOnly", True)
                        # Prefer combined streams (not video-only)
                        # Prefer 720p, then 1080p, then lower resolutions
                        if not video_only:
                            priority = 1000
                        else:
                            priority = 0
                        
                        if height == 720:
                            priority += 100
                        elif height == 1080:
                            priority += 90
                        elif height == 480:
                            priority += 80
                        elif height == 360:
                            priority += 70
                        else:
                            priority += height // 10
                        
                        return priority
                    
                    mp4_streams.sort(key=get_stream_priority, reverse=True)
                    best_video = mp4_streams[0]
                    
                    # If video is video-only, find best audio stream
                    audio_url = None
                    if best_video.get("videoOnly", False) and audio_streams:
                        # Sort audio by bitrate
                        audio_streams.sort(key=lambda x: x.get("bitrate", 0), reverse=True)
                        # Prefer M4A format
                        m4a_streams = [s for s in audio_streams if "m4a" in s.get("mimeType", "").lower() or "mp4" in s.get("mimeType", "").lower()]
                        if m4a_streams:
                            audio_url = m4a_streams[0].get("url")
                        elif audio_streams:
                            audio_url = audio_streams[0].get("url")
                    
                    video_info = VideoInfo(
                        title=data.get("title", "Unknown Title"),
                        description=data.get("description", ""),
                        duration=data.get("duration", 0),
                        thumbnail_url=data.get("thumbnailUrl", ""),
                        uploader=data.get("uploader", "Unknown"),
                        views=data.get("views", 0),
                        video_url=best_video.get("url"),
                        audio_url=audio_url,
                        is_video_only=best_video.get("videoOnly", False),
                        quality=best_video.get("quality", "Unknown")
                    )
                    
                    logger.info(f"Got video info from {instance}: {video_info.title} ({video_info.quality})")
                    return video_info
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout connecting to Piped instance {instance}")
            continue
        except aiohttp.ClientError as e:
            logger.warning(f"Connection error with Piped instance {instance}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error getting video info from {instance}: {e}")
            continue
    
    logger.error(f"All Piped instances failed for video {video_id}")
    return None


async def download_stream(url: str, output_path: str, progress_callback=None) -> bool:
    """
    Download a stream from URL to file
    
    Args:
        url: Stream URL
        output_path: Path to save the file
        progress_callback: Optional callback function(downloaded_bytes, total_bytes)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as response:
                if response.status != 200:
                    logger.error(f"Failed to download stream: HTTP {response.status}")
                    return False
                
                total_size = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            await progress_callback(downloaded, total_size)
                
                logger.info(f"Downloaded {downloaded} bytes to {output_path}")
                return True
                
    except asyncio.TimeoutError:
        logger.error(f"Timeout downloading stream")
        return False
    except Exception as e:
        logger.error(f"Error downloading stream: {e}")
        return False


async def download_youtube_video(
    video_id: str,
    output_dir: str,
    progress_callback=None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Download a YouTube video using Piped API
    
    Args:
        video_id: YouTube video ID
        output_dir: Directory to save the video
        progress_callback: Optional callback for progress updates
    
    Returns:
        Tuple of (output_file_path, video_metadata) or (None, None) if failed
    """
    # Get video info from Piped
    video_info = await get_video_info(video_id)
    
    if not video_info:
        logger.error(f"Failed to get video info for {video_id}")
        return None, None
    
    if not video_info.video_url:
        logger.error(f"No video URL found for {video_id}")
        return None, None
    
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    # Download video
    video_path = os.path.join(output_dir, f"{video_id}_video.mp4")
    
    logger.info(f"Downloading video: {video_info.title}")
    
    if not await download_stream(video_info.video_url, video_path, progress_callback):
        logger.error(f"Failed to download video stream")
        return None, None
    
    # If video-only, download and merge audio
    if video_info.is_video_only and video_info.audio_url:
        audio_path = os.path.join(output_dir, f"{video_id}_audio.m4a")
        
        logger.info(f"Downloading audio stream (video was video-only)")
        
        if await download_stream(video_info.audio_url, audio_path):
            # Merge video and audio using ffmpeg
            output_path = os.path.join(output_dir, f"{video_id}.mp4")
            
            try:
                import subprocess
                
                # Use ffmpeg to merge video and audio
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-strict", "experimental",
                    output_path
                ]
                
                logger.info(f"Merging video and audio with ffmpeg")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    # Clean up temporary files
                    os.remove(video_path)
                    os.remove(audio_path)
                    video_path = output_path
                    logger.info(f"Successfully merged video and audio")
                else:
                    logger.warning(f"ffmpeg merge failed: {result.stderr}")
                    # Keep the video-only file
                    output_path = os.path.join(output_dir, f"{video_id}.mp4")
                    os.rename(video_path, output_path)
                    video_path = output_path
                    
            except subprocess.TimeoutExpired:
                logger.warning("ffmpeg merge timed out, keeping video-only file")
                output_path = os.path.join(output_dir, f"{video_id}.mp4")
                os.rename(video_path, output_path)
                video_path = output_path
            except FileNotFoundError:
                logger.warning("ffmpeg not found, keeping video-only file")
                output_path = os.path.join(output_dir, f"{video_id}.mp4")
                os.rename(video_path, output_path)
                video_path = output_path
        else:
            # Audio download failed, keep video-only
            output_path = os.path.join(output_dir, f"{video_id}.mp4")
            os.rename(video_path, output_path)
            video_path = output_path
    else:
        # Video has audio, just rename
        output_path = os.path.join(output_dir, f"{video_id}.mp4")
        os.rename(video_path, output_path)
        video_path = output_path
    
    # Return metadata
    metadata = {
        "title": video_info.title,
        "description": video_info.description,
        "duration": video_info.duration,
        "thumbnail": video_info.thumbnail_url,
        "uploader": video_info.uploader,
        "views": video_info.views,
        "quality": video_info.quality,
    }
    
    return video_path, metadata


# For testing
if __name__ == "__main__":
    import sys
    
    async def test_download():
        if len(sys.argv) < 2:
            print("Usage: python piped_downloader.py <video_id>")
            return
        
        video_id = sys.argv[1]
        output_dir = "/tmp/piped_test"
        
        print(f"Testing download for video: {video_id}")
        
        result, metadata = await download_youtube_video(video_id, output_dir)
        
        if result:
            print(f"Success! Downloaded to: {result}")
            print(f"Metadata: {metadata}")
        else:
            print("Download failed")
    
    asyncio.run(test_download())
