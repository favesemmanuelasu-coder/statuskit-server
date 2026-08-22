"""
StatusKit Video Processing Server
Uses static FFmpeg binary with libx264 + fonts for watermark
"""

import os
import uuid
import asyncio
import subprocess
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import uvicorn

app = FastAPI(title="StatusKit Video Server")

UPLOAD_DIR = Path("/tmp/statuskit/uploads")
OUTPUT_DIR = Path("/tmp/statuskit/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find available font on startup
def find_font():
    """Find a font file available on this system."""
    candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    ]
    for font in candidates:
        if Path(font).exists():
            print(f"Using font: {font}")
            return font
    # Try fc-list as fallback
    try:
        result = subprocess.run(
            ["fc-list", ":spacing=proportional", "--format=%{file}\n"],
            capture_output=True, text=True, timeout=5
        )
        fonts = [f.strip() for f in result.stdout.split('\n') if f.strip().endswith('.ttf')]
        if fonts:
            print(f"Using font from fc-list: {fonts[0]}")
            return fonts[0]
    except Exception:
        pass
    print("WARNING: No font found, watermark will be disabled")
    return None

FONT_PATH = find_font()


def cleanup_files(*paths):
    for path in paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


@app.get("/")
def root():
    return {"status": "ok", "service": "StatusKit Video Server"}


@app.get("/health")
def health_check():
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout + result.stderr
        has_x264 = "libx264" in output
        ver = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10
        )
        version = ver.stdout.split('\n')[0] if ver.stdout else "unknown"
        return {
            "status": "ok",
            "ffmpeg": "available",
            "libx264": has_x264,
            "version": version,
            "font": FONT_PATH or "not found"
        }
    except Exception as e:
        return {"status": "error", "ffmpeg": str(e), "libx264": False}


@app.post("/compress")
async def compress_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    job_id = str(uuid.uuid4())
    ext = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    input_path = UPLOAD_DIR / f"{job_id}{ext}"
    output_path = OUTPUT_DIR / f"{job_id}_statuskit.mp4"

    try:
        content = await file.read()
        input_path.write_bytes(content)
        size_mb = len(content) / (1024 * 1024)
        print(f"[{job_id}] Received: {file.filename} ({size_mb:.1f} MB)")

        # Build video filter chain
        # Use explicit font path if available, otherwise skip watermark
        if FONT_PATH:
            vf = (
                "scale=-2:'min(1080,ih)',"
                "setsar=1,"
                "format=yuv420p,"
                f"drawtext=text='StatusKit':"
                f"fontfile='{FONT_PATH}':"
                "fontsize=36:"
                "fontcolor=white:"
                "borderw=2:"
                "bordercolor=black:"
                "alpha=0.75:"
                "x=w-tw-20:"
                "y=h-th-20"
            )
        else:
            # No watermark if no font available
            vf = "scale=-2:'min(1080,ih)',setsar=1,format=yuv420p"

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
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()[-3000:]
            print(f"[{job_id}] FFmpeg failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Processing failed: {error_msg}"
            )

        out_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[{job_id}] Done: {out_mb:.1f} MB")

        background_tasks.add_task(
            cleanup_files, str(input_path), str(output_path)
        )

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
