"""
S3 upload helper for video files
"""
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Get S3 credentials from environment
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')


def upload_to_s3(local_file_path: str, s3_key: str) -> str:
    """
    Upload a file to S3 and return the public URL
    
    Args:
        local_file_path: Path to local file
        s3_key: S3 object key (e.g., "videos/1/video.mp4")
    
    Returns:
        Public URL of the uploaded file
    
    Raises:
        Exception: If upload fails
    """
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
        raise Exception("S3 credentials not configured. Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET environment variables.")
    
    try:
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        # Upload file
        logger.info(f"Uploading {local_file_path} to s3://{AWS_S3_BUCKET}/{s3_key}")
        
        s3_client.upload_file(
            local_file_path,
            AWS_S3_BUCKET,
            s3_key,
            ExtraArgs={
                'ContentType': 'video/mp4'
                # ACL removed - bucket policy handles public access
            }
        )
        
        # Generate public URL
        public_url = f"https://{AWS_S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        
        logger.info(f"Upload successful: {public_url}")
        return public_url
        
    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        raise Exception(f"Failed to upload to S3: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}")
        raise


def delete_from_s3(s3_key: str) -> bool:
    """
    Delete a file from S3
    
    Args:
        s3_key: S3 object key to delete
    
    Returns:
        True if successful, False otherwise
    """
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET]):
        logger.error("S3 credentials not configured")
        return False
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        
        s3_client.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        logger.info(f"Deleted s3://{AWS_S3_BUCKET}/{s3_key}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete from S3: {e}")
        return False
