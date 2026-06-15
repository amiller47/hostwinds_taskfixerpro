#!/usr/bin/env python3
"""
Curling Strategy Annotation App
Web interface for marking strategic moments in curling transcripts.

Run: python annotate_app.py
Access: http://localhost:5001 or http://100.114.196.48:5001
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = Path("/home/curl/curling-strategy-data")
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
ANNOTATIONS_DIR = BASE_DIR / "annotations"
FRAMES_DIR = BASE_DIR / "frames"

# Ensure directories exist
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# Current transcript
current_transcript = None
current_index = 0


def load_transcript(transcript_name: str):
    """Load a transcript file."""
    global current_transcript
    path = TRANSCRIPTS_DIR / transcript_name
    if not path.exists():
        return None
    with open(path) as f:
        current_transcript = json.load(f)
    return current_transcript


def load_annotations(transcript_name: str):
    """Load existing annotations for a transcript."""
    # Remove _vision.json suffix if present
    base_name = transcript_name.replace("_vision.json", ".json")
    ann_path = ANNOTATIONS_DIR / f"{base_name.replace('.json', '_annotated.json')}"
    if ann_path.exists():
        with open(ann_path) as f:
            return json.load(f)
    return {"transcript": transcript_name, "annotations": []}


def save_annotation(transcript_name: str, segment_idx: int, is_strategic: bool,
                    game_state: dict, notes: str = ""):
    """Save an annotation."""
    base_name = transcript_name.replace("_vision.json", ".json")
    ann_path = ANNOTATIONS_DIR / f"{base_name.replace('.json', '_annotated.json')}"

    annotations = load_annotations(transcript_name)

    # Check if this segment already annotated
    existing = None
    for ann in annotations["annotations"]:
        if ann["segment_idx"] == segment_idx:
            existing = ann
            break

    if existing:
        # Update existing
        existing["is_strategic"] = is_strategic
        existing["game_state"] = game_state
        existing["notes"] = notes
        existing["annotated_at"] = datetime.now().isoformat()
    else:
        # Add new
        annotations["annotations"].append({
            "segment_idx": segment_idx,
            "is_strategic": is_strategic,
            "game_state": game_state,
            "notes": notes,
            "annotated_at": datetime.now().isoformat()
        })

    with open(ann_path, "w") as f:
        json.dump(annotations, f, indent=2)

    return ann_path


@app.route("/")
def index():
    """Main page - list available transcripts."""
    transcripts = list(TRANSCRIPTS_DIR.glob("*_vision.json"))
    return render_template("index.html",
                          transcripts=[t.name for t in transcripts])


@app.route("/annotate/<transcript_name>")
def annotate(transcript_name):
    """Annotation interface for a transcript."""
    transcript = load_transcript(transcript_name)
    if not transcript:
        return "Transcript not found", 404

    annotations = load_annotations(transcript_name)

    # Get annotation status for each segment
    annotated_idxs = {ann["segment_idx"] for ann in annotations["annotations"]}

    return render_template("annotate.html",
                          transcript_name=transcript_name,
                          transcript=transcript,
                          annotations=annotations,
                          annotated_idxs=annotated_idxs)


@app.route("/api/segment/<transcript_name>/<int:idx>")
def get_segment(transcript_name, idx):
    """Get a specific segment with vision data."""
    transcript = load_transcript(transcript_name)
    if not transcript:
        return jsonify({"error": "Transcript not found"}), 404

    segments = transcript.get("segments", [])
    if idx < 0 or idx >= len(segments):
        return jsonify({"error": "Segment index out of range"}), 400

    segment = segments[idx]

    # Check for existing annotation
    annotations = load_annotations(transcript_name)
    existing = None
    for ann in annotations["annotations"]:
        if ann["segment_idx"] == idx:
            existing = ann
            break

    return jsonify({
        "segment": segment,
        "annotation": existing
    })


@app.route("/api/save", methods=["POST"])
def api_save():
    """Save an annotation."""
    data = request.json
    transcript_name = data.get("transcript_name")
    segment_idx = data.get("segment_idx")
    is_strategic = data.get("is_strategic", False)
    game_state = data.get("game_state", {})
    notes = data.get("notes", "")

    if not transcript_name or segment_idx is None:
        return jsonify({"error": "Missing required fields"}), 400

    path = save_annotation(transcript_name, segment_idx, is_strategic, game_state, notes)

    return jsonify({"success": True, "path": str(path)})


@app.route("/api/stats/<transcript_name>")
def get_stats(transcript_name):
    """Get annotation statistics."""
    annotations = load_annotations(transcript_name)
    transcript = load_transcript(transcript_name)

    if not transcript:
        return jsonify({"error": "Transcript not found"}), 404

    total_segments = len(transcript.get("segments", []))
    annotated = len(annotations["annotations"])
    strategic = sum(1 for a in annotations["annotations"] if a.get("is_strategic"))

    return jsonify({
        "total_segments": total_segments,
        "annotated": annotated,
        "strategic": strategic,
        "not_strategic": annotated - strategic,
        "remaining": total_segments - annotated
    })


@app.route("/frames/<filename>")
def serve_frame(filename):
    """Serve frame images."""
    return send_from_directory(FRAMES_DIR, filename)


@app.route("/export/<transcript_name>")
def export_training_data(transcript_name):
    """Export annotated data for training."""
    transcript = load_transcript(transcript_name)
    annotations = load_annotations(transcript_name)

    if not transcript:
        return jsonify({"error": "Transcript not found"}), 404

    # Build training data
    training_data = []
    for ann in annotations["annotations"]:
        if not ann.get("is_strategic"):
            continue

        idx = ann["segment_idx"]
        if idx >= len(transcript["segments"]):
            continue

        segment = transcript["segments"][idx]

        training_entry = {
            "timestamp": segment.get("start", 0),
            "commentary": segment.get("text", ""),
            "game_state": ann.get("game_state", {}),
            "vision": segment.get("vision", {}),
            "notes": ann.get("notes", "")
        }
        training_data.append(training_entry)

    return jsonify({
        "transcript": transcript_name,
        "total_strategic": len(training_data),
        "training_data": training_data
    })


if __name__ == "__main__":
    print("="*60)
    print("CURLING STRATEGY ANNOTATION APP")
    print("="*60)
    print()
    print("Access at:")
    print("  Local: http://localhost:5001")
    print("  Remote: http://100.114.196.48:5001")
    print()
    print(f"Data directory: {BASE_DIR}")
    print(f"Transcripts: {TRANSCRIPTS_DIR}")
    print(f"Annotations: {ANNOTATIONS_DIR}")
    print()
    app.run(host="0.0.0.0", port=5001, debug=True)