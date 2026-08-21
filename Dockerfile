# Build FFmpeg with libx264 from source — guarantees libx264 support
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    pkg-config \
    yasm \
    nasm \
    wget \
    curl \
    libssl-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Build x264 from source
RUN git clone --depth 1 https://code.videolan.org/videolan/x264.git /tmp/x264 && \
    cd /tmp/x264 && \
    ./configure --prefix=/usr/local --enable-static --enable-shared --disable-cli && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/x264

# Build FFmpeg with libx264
RUN wget -q https://ffmpeg.org/releases/ffmpeg-6.0.tar.bz2 -O /tmp/ffmpeg.tar.bz2 && \
    tar -xf /tmp/ffmpeg.tar.bz2 -C /tmp && \
    cd /tmp/ffmpeg-6.0 && \
    ./configure \
        --prefix=/usr/local \
        --enable-gpl \
        --enable-libx264 \
        --enable-nonfree \
        --enable-openssl \
        --disable-debug \
        --disable-doc \
        --disable-ffplay \
        --disable-filters \
        --enable-filter=scale \
        --enable-filter=drawtext \
        --enable-filter=setsar \
        --enable-filter=format \
        --enable-filter=aresample \
        --enable-filter=volume \
        --disable-programs \
        --enable-ffmpeg \
        --enable-ffprobe \
    && make -j$(nproc) && \
    make install && \
    ldconfig && \
    rm -rf /tmp/ffmpeg* && \
    rm -rf /tmp/ffmpeg-6.0

# Verify libx264 works
RUN ffmpeg -encoders 2>&1 | grep libx264 && echo "libx264 OK"

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY main.py .

# Create temp directories
RUN mkdir -p /tmp/statuskit/uploads /tmp/statuskit/outputs

EXPOSE 8000

CMD ["python3", "main.py"]
