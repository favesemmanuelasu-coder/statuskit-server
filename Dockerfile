FROM python:3.11-slim

# Copy static FFmpeg binary (includes libx264)
COPY --from=mwader/static-ffmpeg:latest /ffmpeg /usr/local/bin/ffmpeg
COPY --from=mwader/static-ffmpeg:latest /ffprobe /usr/local/bin/ffprobe

RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# Install fonts for FFmpeg drawtext watermark
RUN apt-get update && apt-get install -y \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Verify libx264 and fonts
RUN ffmpeg -encoders 2>&1 | grep libx264 && echo "libx264 OK"
RUN fc-list | head -5 && echo "Fonts OK"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN mkdir -p /tmp/statuskit/uploads /tmp/statuskit/outputs

EXPOSE 8000

CMD ["python3", "main.py"]
