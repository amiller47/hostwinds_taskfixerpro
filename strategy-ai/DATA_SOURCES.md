# Curling Strategy AI — Data Sources & Training Plan

## Training Data Strategy

**Goal:** Build a dataset of `{game_state} → {strategic_commentary}` pairs

**Quality over quantity** — 100 well-annotated moments > 1000 weak ones

---

## Video Sources

### Primary: Brier & Scotties (Canadian Championships)
**Why best for training:**
- Expert commentary (Vic Rauter, Cheryl Bernard, Kevin Martin, etc.)
- Clear strategic explanations
- High production quality
- Extensive YouTube archive

**Target videos:**
| Event | Year | Type | Priority |
|-------|------|------|----------|
| Brier Final | 2024 | Men's final | HIGH |
| Scotties Final | 2024 | Women's final | HIGH |
| Brier Final | 2023 | Men's final | HIGH |
| Scotties Final | 2023 | Women's final | HIGH |
| Brier Semifinal | 2024 | High-stakes game | MEDIUM |
| Scotties Semifinal | 2024 | High-stakes game | MEDIUM |

### Secondary: Olympics
- Olympic finals (2022, 2018)
- Good for international perspective
- Commentary sometimes less strategic focus

### Tertiary: Other elite events
- World Championships
- Grand Slam events
- Good for variety, but prioritize Brier/Scotties

---

## Books & Written Resources

### Confirmed
- **"Curl to Win"** — Andy has digital copy
  - Need to extract/convert text
  - Good for strategic principles

### To Find
- "Curling: The Complete Guide" (or similar comprehensive strategy book)
- Competition analysis documents
- Elite curling team playbooks (if available)

---

## Annotation Strategy

### What Makes a "Strategic Moment"?

**Mark as strategic if commentary includes:**

1. **Tactical analysis**
   - "Red should draw to the four-foot here"
   - "Yellow needs to guard — that's a steal opportunity"

2. **Situational reasoning**
   - "With hammer in the 8th, down two, they need to blank"
   - "The ice is running straight today, favor the out-turn"

3. **Game context**
   - Score situation + end number + hammer
   - Team tendencies under pressure

4. **Coaching value**
   - "This is a must-make shot"
   - "They've been struggling with hits all game"

**Don't mark:**
- Pure play-by-play ("Jones throws, it's a draw")
- Generic statements ("Great shot")
- Crowd reactions

---

## Annotation Schema

```json
{
  "segment_idx": 42,
  "timestamp": 1847.3,
  "commentary": "Red should really consider a blank here. They're up two with hammer, no need to force anything.",
  "game_state": {
    "end": 8,
    "score": {"red": 5, "yellow": 3},
    "hammer": "red",
    "shot_number": 14,
    "rocks_in_play": [
      {"color": "red", "position": {"x": 0.2, "y": 1.5}},
      {"color": "yellow", "position": {"x": -0.4, "y": 2.0}}
    ]
  },
  "type": "tactical",
  "reasoning_level": 2,
  "annotation_source": "human"
}
```

**Reasoning levels:**
1. Basic commentary ("Red has two in the house")
2. Situational awareness ("Red should blank with hammer")
3. Strategic coaching ("Ice is straight, try the out-turn draw")

---

## Target: 1000 Annotated Moments

**Breakdown:**
- 500 from Brier/Scotties finals
- 200 from Olympic finals
- 200 from semifinals
- 100 from other elite events

**Time estimate:**
- 1 hour of video → ~50-100 strategic moments
- 20 hours of video → target dataset

---

## Quality Control

1. **Two-pass annotation**
   - First pass: Mark timestamps
   - Second pass: Verify game state

2. **Inter-annotator agreement**
   - Have Andy review subset
   - Ensure consistent marking criteria

3. **Diverse coverage**
   - Different game situations (close games, blowouts, last-end drama)
   - Different shot types (draws, takeouts, guards)
   - Both men's and women's games

---

*Last updated: June 15, 2026*