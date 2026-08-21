# mwader/static-ffmpeg contains a fully static FFmpeg binary
# compiled with ALL codecs including libx264, libx265, libvpx etc.
# No dependency issues, works on any Linux environment.
FROM python:3.11-slim

# Copy static FFmpeg binary (includes libx264 compiled in)
COPY --from=mwader/static-ffmpeg:latest /ffmpeg /usr/local/bin/ffmpeg
COPY --from=mwader/static-ffmpeg:latest /ffprobe /usr/local/bin/ffprobe

# Make executable
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

# Verify libx264 is included
RUN ffmpeg -encoders 2>&1 | grep libx264 && echo "libx264 OK" || (echo "libx264 MISSING" && exit 1)

# Install Python packages
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server
COPY main.py .

# Temp dirs
RUN mkdir -p /tmp/statuskit/uploads /tmp/statuskit/outputs

EXPOSE 8000

CMD ["python3", "main.py"]
