# Curling Strategy AI — Project Documentation

## Vision

Build an AI curling strategy expert that provides real-time strategic commentary integrated with the FCC Sheet5 Vision System.

**Goal:** Train a model that understands curling strategy and can commentate on games in real-time.

---

## What We Built (June 14-15, 2026)

### Phase 1: Data Collection Pipeline ✅

**Location:** `/home/curl/curling_vision/strategy-ai/`

| Tool | Purpose | Status |
|------|---------|--------|
| `download_video.py` | Download YouTube videos | ✅ Working |
| `transcribe_xai.py` | Transcribe using xAI Speech-to-Text | ✅ Working |
| `transcribe_chunked.py` | Handle large videos (30-min chunks) | ✅ Working |
| `sync_vision_transcript.py` | Extract frames + run rock detection | ✅ Working |
| `annotate_app.py` | Web interface for marking strategic moments | ✅ Working |

### First Dataset

**Video:** 2024 Scotties Tournament of Hearts Final
- Duration: 450 minutes (2.7 hours)
- Transcript: 15,578 words across 432 segments
- Vision-enriched: 72 segments analyzed, 37 with rocks detected

---

## Key Discovery: Vision Model Works on Broadcast Video

The FCC curling vision model successfully detects rocks on Scotties/Brier overhead camera views:

| Frame | Detected | Confidence |
|-------|----------|------------|
| 1:00 | 1 yellow rock | 77% |
| 3:00 | 6 rocks (4 red, 2 yellow) | 90%+ |
| Various | House detection | 57-70% |

**This means we can auto-populate game state from video!**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA COLLECTION PIPELINE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  YouTube Video ──► yt-dlp ──► Video File                    │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              xAI Speech-to-Text API                 │   │
│  │         (transcribe_chunked.py)                    │   │
│  │                                                     │   │
│  │  Video ──► 30-min chunks ──► Transcription         │   │
│  │                              (word-level timestamps)│   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Vision Model Integration                  │   │
│  │         (sync_vision_transcript.py)                 │   │
│  │                                                     │   │
│  │  Transcript timestamps ──► Frame extraction         │   │
│  │                              │                      │   │
│  │                              ▼                      │   │
│  │  ┌───────────────────────────────────────────┐     │   │
│  │  │  FCC Rock Detection Model (Roboflow)     │     │   │
│  │  │                                           │     │   │
│  │  │  Frame ──► Rock positions               │     │   │
│  │  │         ──► House detection              │     │   │
│  │  │         ──► Score analysis                │     │   │
│  │  └───────────────────────────────────────────┘     │   │
│  │                              │                      │   │
│  │                              ▼                      │   │
│  │  Enriched Transcript (JSON)                        │   │
│  │  {segment, text, vision: {rocks, score}}           │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           Web Annotation Interface                  │   │
│  │         (annotate_app.py - Flask)                  │   │
│  │                                                     │   │
│  │  Shows: Transcript + Frame + Vision Data            │   │
│  │  Input: Strategic? (S/N) + Game State              │   │
│  │  Output: Annotated training data                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│              Training Dataset (JSONL)                       │
│   {game_state, commentary, vision_data, is_strategic}      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Roadmap

### Phase 1: Data Collection ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Video download tool | ✅ | `download_video.py` |
| Transcription (xAI STT) | ✅ | `transcribe_chunked.py` |
| Vision sync | ✅ | `sync_vision_transcript.py` |
| Annotation interface | ✅ | `annotate_app.py` |
| First video processed | ✅ | Scotties 2024 Final |

**Remaining Phase 1 Work:**
- [ ] Annotate 100+ strategic moments from first video
- [ ] Download Brier finals (more games)
- [ ] Digitize "Curl to Win" book for strategic principles
- [ ] Build training dataset export

### Phase 2: Model Training 🔜 NEXT

| Task | Status | Notes |
|------|--------|-------|
| Collect 1000+ annotations | 🔴 Blocked on Phase 1 | Need ~20 hours of video |
| Choose base model | 🔴 Pending | Llama 3.1 8B or Mistral 7B |
| Fine-tune on curling data | 🔴 Pending | Rocky's Mac mini (16GB) |
| Evaluate against held-out games | 🔴 Pending | Test on unseen video |

**Hardware:** Rocky's Mac mini (16GB unified memory) for training, or Pi 5 for inference

### Phase 3: Vision Integration 🔴 BLOCKED

| Task | Status | Notes |
|------|--------|-------|
| Build `strategy_engine.py` | 🔴 Pending | Game state → commentary |
| Integrate with `game_tracker.py` | 🔴 Pending | Real-time input |
| Add TTS output | 🔴 Pending | Optional: use Curly's TTS model |
| Real-time pipeline | 🔴 Pending | Vision → Strategy → Voice |

**Integration Point:** FCC Sheet5 Vision System (`/home/curl/curling_vision/`)

---

## Annotation Workflow

1. **Start the app:**
   ```bash
   cd /home/curl/curling_vision/strategy-ai
   source ../venv/bin/activate
   python annotate_app.py
   ```

2. **Open browser:** `http://100.114.196.48:5001` (Tailscale) or `http://192.168.1.239:5001` (LAN)

3. **Select transcript** (e.g., "Brier_2024_Final_transcript_vision.json")

4. **For each segment:**
   - Read the commentary text
   - Review vision data (rock counts, score)
   - Press `S` for strategic, `N` for not strategic
   - Optionally fill in game state (end, score, hammer)
   - Auto-advances to next segment

5. **Export:** Click "Export" to download training data JSON

---

## Files & Locations

```
/home/curl/curling_vision/strategy-ai/
├── PROJECT.md                    # This file
├── DATA_SOURCES.md               # Training data strategy
├── annotate_app.py               # Web annotation interface
├── templates/
│   ├── index.html                # Transcript list page
│   └── annotate.html              # Annotation interface
└── tools/
    ├── download_video.py         # YouTube download
    ├── transcribe_xai.py         # xAI STT transcription
    ├── transcribe_chunked.py     # Large video handling
    ├── sync_vision_transcript.py  # Vision integration
    └── test_vision.py            # Vision model test

/home/curl/curling-strategy-data/
├── videos/                       # Downloaded videos
├── transcripts/                  # Transcriptions
│   ├── Brier_2024_Final_transcript.json
│   └── Brier_2024_Final_transcript_vision.json
├── frames/                       # Extracted frames for vision
└── annotations/                  # Human annotations
```

---

## Git Repository

**Location:** `amiller47/hostwinds_taskfixerpro` (same as curling vision)

**Path:** `strategy-ai/`

**Note:** This is in the same repo as the curling vision system for easy integration.

---

## API Keys

| Service | Purpose | Location |
|---------|---------|----------|
| xAI STT | Transcription | `strategy-ai/tools/.env` (not committed) |
| Roboflow | Rock detection | `/home/curl/curling_config.json` |

---

## Next Steps (Prioritized)

1. **Annotate the Scotties video** — Use the web interface to mark strategic moments
2. **Download more videos** — Brier 2024 Final, Olympics finals
3. **Process and sync** — Run vision sync on new videos
4. **Build dataset** — Export annotations to JSONL format
5. **Start Phase 2** — Fine-tune model when we have 1000+ annotations

---

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Videos processed | 5+ | 1 |
| Strategic moments annotated | 1000+ | 0 |
| Model accuracy (commentary quality) | TBD | — |
| Real-time latency | <2s | — |

---

*Last updated: June 15, 2026*