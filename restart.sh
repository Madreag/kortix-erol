#!/bin/bash
# ============================================
# Kortix Suna - Restart Services (WSL)
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping services..."
"$SCRIPT_DIR/stop.sh"

echo ""
echo "Starting services..."
"$SCRIPT_DIR/start.sh"
