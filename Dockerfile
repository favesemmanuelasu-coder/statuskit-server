# Use Ubuntu with FFmpeg built from source including libx264
FROM ubuntu:22.04

# Prevent interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install FFmpeg with full codec support including libx264
RUN apt-get update && apt-get install -y \
    ffmpeg \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Verify libx264 is available
RUN ffmpeg -encoders 2>&1 | grep libx264 || echo "WARNING: libx264 not found"

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy server code
COPY main.py .

# Create temp directories
RUN mkdir -p /tmp/statuskit/uploads /tmp/statuskit/outputs

# Expose port
EXPOSE 8000

# Start server
CMD ["python3", "main.py"]
