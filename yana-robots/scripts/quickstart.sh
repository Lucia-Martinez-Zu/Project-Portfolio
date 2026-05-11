#!/bin/bash
# Yana Robots — quick start script
set -e

echo "🤖 Yana Robots — Quick Start"
echo "================================"

if [ ! -d ".venv" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv .venv
fi

echo "📦 Activating venv & installing dependencies..."
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "🚀 Starting Yana Robots on http://localhost:5000"
echo "   (Ctrl+C to stop)"
echo ""

python run.py
