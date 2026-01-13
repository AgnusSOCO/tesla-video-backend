FROM python:3.12-slim

# Install ffmpeg for video processing
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code and cookies
COPY bot.py .
COPY video_upload_handler.py .
COPY file_link_handler.py .
COPY s3_upload.py .
COPY piped_downloader.py .
COPY youtube_cookies.txt .

# Create directory for video downloads
RUN mkdir -p /tmp/tesla-videos

# Run the bot
CMD ["python", "bot.py"]
