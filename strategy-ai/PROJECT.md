# Curling Strategy AI — Project Documentation

## Vision

Build an AI curling strategy expert that provides real-time strategic commentary integrated with the FCC Sheet5 Vision System.

## Use Cases

1. **Broadcast Commentary** — Real-time analysis during club games
2. **Coaching Advice** — Strategic recommendations for players during play
3. **Post-Game Analysis** — Break down key moments and decision points

## Project Location

`/home/curl/curling-strategy-data/` (on curl-pi5-canakit)

---

## Three-Phase Roadmap

### Phase 1: Data Collection & Knowledge Base
**Hardware:** Pi 5 (curl-pi5-canakit)
**Duration:** 4-6 weeks
**Status:** 🟡 Starting

**Goal:** Build a dataset of `{game_state} → {strategic_commentary}` pairs.

**Steps:**
1. Download Brier/Scotties/Olympics videos from YouTube
2. Transcribe commentary using Whisper
3. Annotate strategic moments with game state
4. Target: 1000+ annotated moments

**Deliverables:**
- `/home/curl/curling-strategy-data/videos/` — Downloaded videos
- `/home/curl/curling-strategy-data/transcripts/` — Whisper transcriptions
- `/home/curl/curling-strategy-data/annotations/` — Annotated strategic moments
- `/home/curl/curling-strategy-data/dataset.jsonl` — Training dataset

**Training Data Sources:**
- Brier (Canadian Men's Championship) — YouTube
- Scotties (Canadian Women's Championship) — YouTube
- Olympics — YouTube (after Brier/Scotties)
- "Curl to Win" by Andy's digital copy
- Strategy books/guides (TBD)

---

### Phase 2: Model Training
**Hardware:** Rocky's Mac mini (16GB unified memory) or Pi 5
**Duration:** 4-8 weeks
**Status:** 🔴 Blocked (waiting for Phase 1 data)

**Goal:** Fine-tune an LLM to generate strategic commentary from game state.

**Approach:**
- Fine-tune Llama 3.1 8B or Mistral 7B
- Training on `{game_state, commentary}` pairs
- Evaluate against held-out games

**Deliverables:**
- Fine-tuned model weights
- Inference pipeline
- Evaluation metrics

**Model Candidates:**
| Model | Size | Pros | Cons |
|-------|------|------|------|
| Llama 3.1 8B | Small | Runs on Pi 5, fast | Limited reasoning |
| Mistral 7B | Small | Good performance | Needs fine-tuning |
| GPT-4 / Claude API | Large | Best reasoning | Costs money, latency |

**Recommendation:** Start with Llama 3.1 8B fine-tuned locally.

---

### Phase 3: Vision Integration
**Hardware:** Pi 5 (with Vision System)
**Duration:** 2-4 weeks
**Status:** 🔴 Blocked (waiting for Phase 2 model)

**Goal:** Connect trained model to FCC Sheet5 Vision System.

**Pipeline:**
```
Vision System → Game State JSON → Strategy Model → Commentary Text → TTS → Speaker
```

**What We Already Have:**
- Rock positions (JSON from vision system)
- Game state (score, end, hammer, shot number)
- Shot classification (draw, takeout, guard)

**What We Need:**
- Strategic reasoning prompt construction
- Model inference pipeline
- Output formatting (short, punchy commentary)
- Integration with Curly's TTS model (optional)

**Deliverables:**
- `strategy_engine.py` — Game state → commentary
- Integration with existing `game_tracker.py`
- Real-time commentary output

---

## Directory Structure

```
/home/curl/curling-strategy-data/
├── PROJECT.md              # This file
├── videos/                 # Downloaded curling videos
│   ├── brier_2024_final.mp4
│   ├── scotties_2024_final.mp4
│   └── ...
├── transcripts/            # Whisper transcriptions
│   ├── brier_2024_final.json
│   └── ...
├── annotations/            # Annotated strategic moments
│   ├── brier_2024_final_annotated.json
│   └── ...
├── dataset.jsonl           # Final training dataset
├── tools/                  # Annotation tools
│   ├── download_video.py
│   ├── transcribe.py
│   └── annotate.py
└── models/                 # (Phase 2) Fine-tuned models
    └── ...
```

## Game State Schema

```json
{
  "end_number": 8,
  "score": {"red": 5, "yellow": 3},
  "hammer": "red",
  "shot_number": 12,
  "rocks_in_play": [
    {"color": "red", "position": {"x": 0.5, "y": 2.1}},
    {"color": "yellow", "position": {"x": -0.3, "y": 1.8}}
  ],
  "rock_counts": {"red": 3, "yellow": 2},
  "last_shot": {"type": "draw", "result": "made"},
  "game_context": "final end, close game"
}
```

## Commentary Output Schema

```json
{
  "strategic_assessment": "Red should draw to the four-foot here.",
  "reasoning": "They're down two with hammer in the 8th. A draw for two ties the game.",
  "key_factors": ["hammer advantage", "score situation", "end number"],
  "confidence": 0.85
}
```

---

## Progress Log

### 2026-06-14 — Project Started
- Created PROJECT.md
- Created directory structure
- Set up Python virtual environment
- Installed yt-dlp and openai packages
- Created tools:
  - `download_video.py` — Download YouTube videos
  - `transcribe_xai.py` — Transcribe using xAI Speech-to-Text API
  - `transcribe_chunked.py` — Handle large videos (splits into 30-min chunks)
  - `annotate.py` — Interactive annotation tool

### 2026-06-15 — First Video Transcribed
- Downloaded: 2024 Scotties Tournament of Hearts Final (URL: https://youtu.be/1ftIoA8zRqg)
- Duration: 450 minutes (2.7 hours)
- Transcript: 15,578 words across 432 segments
- File: `transcripts/Brier_2024_Final_transcript.json`
- Found strategic commentary examples in transcript

### Architecture Decision
Full Whisper with PyTorch too heavy for Pi 5 (426MB PyTorch + 542MB CUDA).
**Decision:** Use xAI Speech-to-Text API instead of OpenAI Whisper.
- Uses existing xAI API key from LeaderQuest project
- No additional cost for transcription
- Word-level timestamps supported
- Curling keyterms added for better recognition
- Large videos split into 30-minute chunks for reliability

### xAI STT API
- Endpoint: `https://api.x.ai/v1/stt`
- Supports: word-level timestamps, diarization, keyterms
- 500MB max file size, but long files timeout — use chunks
- Already have API key configured

### Next Steps
1. ✅ xAI API key configured
2. ✅ First video downloaded and transcribed
3. ⏳ Annotate strategic moments with `annotate.py`
4. Build initial dataset of 100 annotated moments
5. Download more Brier/Scotties/Olympics videos

---

## Related Projects

- **FCC Sheet5 Vision System** — `/home/curl/curling_vision/`
- **The Syndicate** — Distributed AI team coordination
- **Curly's TTS Model** — Audio synthesis (optional Phase 3 integration)

---

*Last updated: June 14, 2026*