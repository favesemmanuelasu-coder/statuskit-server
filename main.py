"""
StatusKit Video Processing Server
==================================
Runs FFmpeg with libx264 on the server side — exactly like Pure Status.
Deploy free on Railway.app or Render.com

FFmpeg command produces:
  - H.264 High profile (libx264)
  - 1613 kbps video bitrate
  - bt709 color space (prevents WhatsApp re-compression)
  - 1080p max resolution
  - AAC 126 kbps audio
"""

import os
import uuid
import asyncio
import subprocess
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

app = FastAPI(title="StatusKit Video Server")

# Temp directories
UPLOAD_DIR = Path("/tmp/statuskit/uploads")
OUTPUT_DIR = Path("/tmp/statuskit/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def cleanup_files(*paths):
    """Delete temp files after response is sent."""
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/")
def health():
    return {"status": "ok", "service": "StatusKit Video Server"}


@app.get("/health")
def health_check():
    # Check ffmpeg is available
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10
        )
        has_x264 = "libx264" in result.stdout or "libx264" in result.stderr
        return {
            "status": "ok",
            "ffmpeg": "available",
            "libx264": has_x264
        }
    except Exception as e:
        return {"status": "error", "ffmpeg": str(e)}


@app.post("/compress")
async def compress_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Accept a video file, compress it with FFmpeg libx264,
    return the compressed file.
    """
    # Validate file type
    allowed = {
        "video/mp4", "video/quicktime", "video/x-msvideo",
        "video/mpeg", "video/webm", "video/3gpp",
        "application/octet-stream"
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed:
        # Be lenient — check extension too
        ext = Path(file.filename or "").suffix.lower()
        if ext not in {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".3gp", ".webm"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {content_type}"
            )

    # Save uploaded file
    job_id = str(uuid.uuid4())
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    input_path = UPLOAD_DIR / f"{job_id}{ext}"
    output_path = OUTPUT_DIR / f"{job_id}_statuskit.mp4"

    try:
        # Write upload to disk
        content = await file.read()
        input_path.write_bytes(content)

        file_size_mb = len(content) / (1024 * 1024)
        print(f"[{job_id}] Received: {file.filename} ({file_size_mb:.1f} MB)")

        # ── FFmpeg command — exact Pure Status specs ───────────────────────
        #
        # -c:v libx264          Software H.264 encoder
        # -profile:v high        High profile (same as Pure Status)
        # -level:v 3.1           Level 3.1
        # -crf 23               Quality factor (lower = better)
        # -maxrate 1613k         Bitrate ceiling matching Pure Status
        # -bufsize 3226k         VBV buffer = 2× maxrate
        # scale filter           1080p max, keep AR, even dims
        # -colorspace bt709      CRITICAL: prevents WhatsApp re-compression
        # -color_primaries bt709
        # -color_trc bt709
        # -x264-params           Force bt709 in x264 NAL headers
        # -movflags +faststart   MP4 optimised for streaming
        # -c:a aac               AAC audio
        # -b:a 126k              Exact Pure Status audio bitrate
        # -ar 44100              44.1 kHz sample rate
        #
        vf = (
            "scale=-2:'min(1080,ih)',"
            "setsar=1,"
            "format=yuv420p,"
            "drawtext=text='StatusKit':"
            "font=sans:"
            "fontsize=36:"
            "fontcolor=white:"
            "borderw=2:"
            "bordercolor=black:"
            "alpha=0.75:"
            "x=w-tw-20:"
            "y=h-th-20"
        )

        cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level:v", "3.1",
            "-crf", "23",
            "-maxrate", "1613k",
            "-bufsize", "3226k",
            "-vf", vf,
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-x264-params", "colormatrix=bt709",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "126k",
            "-ar", "44100",
            "-ac", "2",
            "-y",
            str(output_path),
        ]

        print(f"[{job_id}] Running FFmpeg...")

        # Run FFmpeg
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()[-2000:]  # Last 2000 chars of error
            print(f"[{job_id}] FFmpeg failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Video processing failed: {error_msg}"
            )

        output_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[{job_id}] Done: {output_size_mb:.1f} MB")

        # Clean up input after sending response
        background_tasks.add_task(cleanup_files, str(input_path), str(output_path))

        return FileResponse(
            path=str(output_path),
            media_type="video/mp4",
            filename="statuskit_optimized.mp4",
        )

    except HTTPException:
        cleanup_files(str(input_path), str(output_path))
        raise
    except Exception as e:
        cleanup_files(str(input_path), str(output_path))
        print(f"[{job_id}] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
