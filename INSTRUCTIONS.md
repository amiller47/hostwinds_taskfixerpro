# Quick Start Instructions — Curling Vision System

## What's Working (April 11, 2026)

- ✅ Game state machine (detects throws, tracks possession)
- ✅ Dashboard server (Flask on port 5000)
- ✅ Real-time video → dashboard bridge
- ✅ Rock detection via Roboflow REST API
- ✅ **Flexible video sources** (RTSP, YouTube, USB, files)

---

## Video Sources Supported

The system now accepts **any video source**:

| Source Type | Example |
|-------------|--------|
| Local file | `/home/curl/Videos/game.mp4` |
| RTSP stream | `rtsp://admin:pass@192.168.1.233:554/stream` |
| YouTube | `https://youtube.com/watch?v=abc123` |
| USB camera | `usb:0` or just `0` |
| HTTP stream | `http://server:port/stream.m3u8` |
| Any yt-dlp site | Vimeo, Twitch, Dailymotion, etc. |

**Note:** For YouTube/other streaming sites, yt-dlp is used to extract the direct stream URL.

## Quick Start

### 1. Start the Dashboard Server

```bash
cd /home/curl/curling_vision
python3 scripts/dashboard_server.py
```

Dashboard will be at: **http://localhost:5000/**

JSON API: **http://localhost:5000/curling_data.json**

### 2. Process a Video (with live dashboard updates)

```bash
# In a new terminal:
cd /home/curl/curling_vision
python3 scripts/realtime_dashboard.py --video <SOURCE> [options]
```

**Video Sources:**
```bash
# Local file:
python3 scripts/realtime_dashboard.py --video /home/curl/Videos/game.mp4 --frames 200

# RTSP stream (live camera):
python3 scripts/realtime_dashboard.py --video rtsp://admin:pass@192.168.1.233:554/stream

# YouTube video:
python3 scripts/realtime_dashboard.py --video https://youtube.com/watch?v=abc123

# USB camera:
python3 scripts/realtime_dashboard.py --video usb:0
```

**To also upload to Hostwinds:**
```bash
python3 scripts/realtime_dashboard.py --video <SOURCE> --upload
```

**Options:**
- `--video` : near_full, far_full, near_crop, far_crop
- `--frames` : Number of frames to process (0 = all)
- `--skip` : Process every Nth frame (5 is good)
- `--start` : Start at this frame number

### 3. View Results

Open **http://localhost:5000/** in a browser on the Pi, or from another machine:
**http://192.168.1.110:5000/**

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/dashboard_server.py` | Flask dashboard server |
| `scripts/realtime_dashboard.py` | Video processing → dashboard |
| `scripts/game_tracker.py` | State machine logic |
| `static/index.html` | Dashboard HTML |
| `dashboard_data.json` | Live game state |
| `config/calibration.json` | Camera calibration |

### 3. Coaching Review Tool

```bash
# Initialize database
python3 scripts/game_recorder.py

# View coaching data
# Open: http://localhost:5000/coach
```

**What's recorded:**
- Games (teams, score, date)
- Ends (hammer, score)
- Shots (team, type, rock positions, result)

**Search capabilities:**
- By team: "Show me all red team shots"
- By type: "Show me all takeouts"
- By result: "Show me all missed shots"

---

## Test Videos

| Name | Path |
|------|------|
| near_full | `/home/curl/Videos/curling/cam2_20260330_194005.mp4` |
| far_full | `/home/curl/Videos/curling/cam1_20260330_194005.mp4` |
| near_crop | `/home/curl/Videos/sheet5NearCrop.mp4` |
| far_crop | `/home/curl/Videos/sheet5FarCrop.mp4` |

---

## What to Expect

**Processing speed:** ~0.9 fps on Pi (REST API)

**Dashboard updates:** Every 5 frames

**Game state cycle:**
```
idle → delivery_in_progress → rock_in_flight → rocks_settling → throw_complete → idle
```

**Test results (April 10):**
- 500 frames processed
- 5 throws detected correctly
- Possession alternated between teams

---

## Troubleshooting

**Dashboard not loading?**
- Make sure Flask server is running
- Check port 5000 is available: `netstat -tlnp | grep 5000`

**No throws detected?**
- Try starting later in the video (`--start 2000`)
- The video starts mid-game, deliveries are sparse in early frames

**API errors?**
- Check internet connection
- Roboflow API may rate-limit if processing too fast

---

## Next Steps (Work in Progress)

- [ ] Wide camera integration (cam3)
- [ ] Full end tracking (16 throws)
- [ ] Scoring calculation
- [ ] Deploy to Hostwinds

---

Questions? Ask Sweepie! 🧹