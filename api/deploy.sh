#!/bin/bash
# Deploy curling dashboard to Hostwinds
# Run from: /home/curl/curling_vision/

echo "🧹 Preparing curling dashboard for Hostwinds deployment..."

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

# Create deployment package
DEPLOY_DIR="/tmp/curling_deploy_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$DEPLOY_DIR/curling"
mkdir -p "$DEPLOY_DIR/curling/js"
mkdir -p "$DEPLOY_DIR/curling/api"
mkdir -p "$DEPLOY_DIR/curling/data"

# Copy static files
echo "📄 Copying static files..."
cp "$SCRIPT_DIR/static/index.html" "$DEPLOY_DIR/curling/"
cp "$SCRIPT_DIR/static/coach.html" "$DEPLOY_DIR/curling/"
cp "$SCRIPT_DIR/static/bingo.html" "$DEPLOY_DIR/curling/"
cp "$SCRIPT_DIR/static/shot.html" "$DEPLOY_DIR/curling/"
cp "$SCRIPT_DIR/static/js/config.js" "$DEPLOY_DIR/curling/js/"

# Copy API files
echo "⚙️  Copying API files..."
cp "$SCRIPT_DIR"/api/*.php "$DEPLOY_DIR/curling/api/"

# Copy data files
echo "📊 Copying data files..."
cp "$SCRIPT_DIR/data/games.db" "$DEPLOY_DIR/curling/data/" 2>/dev/null || echo "   (games.db will be created on first use)"
cp "$SCRIPT_DIR/data/dashboard_data.json" "$DEPLOY_DIR/curling/data/" 2>/dev/null || echo "   (dashboard_data.json not found - upload manually)"

# Add .htaccess
cp "$SCRIPT_DIR/api/.htaccess" "$DEPLOY_DIR/curling/"

# Create zip for easy upload
echo "📦 Creating deployment package..."
cd "$DEPLOY_DIR"
zip -r "/tmp/curling_dashboard.zip" curling

echo ""
echo "✅ Deployment package ready: /tmp/curling_dashboard.zip"
echo ""
echo "📂 Contents:"
ls -la "$DEPLOY_DIR/curling/"
echo ""
echo "📤 To deploy to Hostwinds:"
echo "   1. Download /tmp/curling_dashboard.zip"
echo "   2. Upload to public_html/ on Hostwinds"
echo "   3. Extract to create curling/ folder"
echo "   4. Set permissions: chmod 755 data/"
echo ""
echo "🌐 Dashboard will be at: https://yourdomain.com/curling/"