# StatusKit Server — Deployment Guide

## How it works
1. Flutter app uploads video to this server
2. Server runs FFmpeg with libx264 (same as Pure Status)
3. Server returns compressed HD video
4. App downloads and user posts to WhatsApp Status

---

## Deploy FREE on Railway.app (Recommended — 5 minutes)

### Step 1 — Create GitHub repository
1. Go to github.com → New repository
2. Name it: `statuskit-server`
3. Upload these 4 files:
   - `main.py`
   - `requirements.txt`
   - `Dockerfile`
   - `railway.json`

### Step 2 — Deploy on Railway
1. Go to railway.app
2. Sign up with GitHub (free)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select `statuskit-server`
5. Railway automatically detects the Dockerfile and deploys
6. Wait 2-3 minutes for deployment

### Step 3 — Get your server URL
1. In Railway dashboard, click your project
2. Click "Settings" → "Domains"
3. Click "Generate Domain"
4. Copy the URL — looks like: `https://statuskit-server-production.up.railway.app`

### Step 4 — Update Flutter app
Open `lib/services/video_processing_service.dart`
Find this line:
```dart
static const String serverUrl = 'https://YOUR-SERVER-URL.railway.app';
```
Replace with your actual URL:
```dart
static const String serverUrl = 'https://statuskit-server-production.up.railway.app';
```

### Step 5 — Run the app
```bash
flutter clean
flutter pub get
flutter run
```

---

## Railway Free Tier Limits
- 500 hours/month compute (enough for ~1000 videos)
- 1 GB RAM
- Files are temporary (deleted after each request)

## Alternative: Render.com
1. Go to render.com → New Web Service
2. Connect GitHub repo
3. Select "Docker" environment
4. Deploy — free tier available

---

## Test the server
After deploying, open browser and go to:
```
https://YOUR-SERVER-URL.railway.app/health
```
Should return:
```json
{"status": "ok", "ffmpeg": "available", "libx264": true}
```

If `libx264` is `true` — everything is working perfectly.
