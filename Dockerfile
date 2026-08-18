# Use Python with FFmpeg pre-installed
FROM jrottenberg/ffmpeg:6.0-ubuntu AS ffmpeg
FROM python:3.11-slim

# Copy FFmpeg binaries from the ffmpeg image
COPY --from=ffmpeg /usr/local /usr/local

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY main.py .

# Create temp directories
RUN mkdir -p /tmp/statuskit/uploads /tmp/statuskit/outputs

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "main.py"]
