#!/bin/bash
# Setup script for Curling Strategy AI project
# Run once after cloning

set -e

PROJECT_DIR="/home/curl/curling-strategy-data"

echo "🥌 Setting up Curling Strategy AI project..."
echo ""

# Create directory structure
echo "📁 Creating directories..."
mkdir -p "$PROJECT_DIR"/{videos,transcripts,annotations,tools,models}

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --quiet yt-dlp openai

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Set OPENAI_API_KEY environment variable (for Whisper API)"
echo "   2. Download a video: python tools/download_video.py <youtube_url>"
echo "   3. Transcribe: python tools/transcribe.py videos/<file>.mp4"
echo "   4. Annotate: python tools/annotate.py transcripts/<file>_transcript.json"
echo ""
echo "💡 For API key, contact Andy or use: export OPENAI_API_KEY=sk-..."