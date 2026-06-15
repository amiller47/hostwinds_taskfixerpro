# Curling Strategy AI — Session Summary (June 15, 2026)

## Project Started

Created new AI curling strategy project to train a model for real-time strategic commentary.

### What We Built

**Location:** `/home/curl/curling-strategy-data/`

**Tools:**
- `download_video.py` — Download YouTube videos
- `transcribe_xai.py` — Transcribe using xAI Speech-to-Text API
- `transcribe_chunked.py` — Handle large videos by splitting into chunks
- `annotate.py` — Interactive annotation tool

**Architecture:**
- Uses xAI Speech-to-Text API (existing API key from LeaderQuest)
- Splits large videos into 30-minute chunks for reliable transcription
- Outputs JSON with word-level timestamps

---

## First Video Transcribed

**Video:** 2024 Scotties Tournament of Hearts Final (misnamed as Brier)
- **URL:** https://youtu.be/1ftIoA8zRqg
- **Duration:** 450 minutes (2.7 hours)
- **Transcript:** 15,578 words across 432 segments
- **File:** `transcripts/Brier_2024_Final_transcript.json` (actually Scotties)

### Sample Strategic Commentary Found

| Time | Commentary |
|------|-----------|
| 08:24 | "this really should be a classic... Points for and against, they're scoring their opponents by a ton..." |
| 09:25 | "play it a little simple in the first half, they should be more comfortable in that second half with all their finals experience" |
| 11:58 | "you're sliding out and thinking, 'Oh, it's really gonna curl here,' so then you give..." |

### Next Steps

1. **Annotate strategic moments** — Run `annotate.py` to mark coaching-worthy commentary
2. **Download more videos** — Brier finals, more Scotties, Olympics
3. **Build dataset** — Target 100+ annotated strategic moments
4. **Digitize "Curl to Win"** — Extract strategic principles from book

---

## Files Created

```
curling-strategy-data/
├── PROJECT.md              # Full documentation
├── DATA_SOURCES.md         # Training data strategy
├── videos/
│   ├── Brier_2024_Final.mp4    # Actually Scotties 2024 Final
│   ├── Brier_2024_Final.mp3     # Extracted audio
│   └── chunks/                  # 30-min segments
├── transcripts/
│   └── Brier_2024_Final_transcript.json
├── annotations/             # (empty, ready for use)
├── tools/
│   ├── download_video.py
│   ├── transcribe_xai.py
│   ├── transcribe_chunked.py
│   ├── annotate.py
│   └── setup.sh
└── venv/                    # Python virtual environment
```

---

## Technical Notes

- xAI STT API handles 30-minute chunks reliably (500MB limit, but long files timeout)
- Word-level timestamps preserved for precise annotation
- Curling keyterms added: hammer, draw, takeout, guard, house, button, etc.

---

*Ready for annotation phase*