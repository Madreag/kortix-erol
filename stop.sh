#!/bin/bash
# ============================================
# Kortix Suna - Stop Services (WSL)
# ============================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Kortix Suna - Stopping Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to stop a service by PID file
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/$name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null
            sleep 1
            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null
            fi
            echo -e "${GREEN}  ✓ Stopped $name (PID: $pid)${NC}"
        else
            echo -e "${YELLOW}  ⚠ $name was not running${NC}"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}  ⚠ No PID file for $name${NC}"
    fi
}

# Stop Frontend
echo -e "${YELLOW}[1/3] Stopping Frontend...${NC}"
stop_service "frontend"
# Also kill any stray Next.js processes
pkill -f "next dev" 2>/dev/null || true
pkill -f "pnpm run dev" 2>/dev/null || true

# Stop Backend
echo -e "${YELLOW}[2/3] Stopping Backend...${NC}"
stop_service "backend"
# Also kill any stray backend processes
pkill -f "uv run python api.py" 2>/dev/null || true
pkill -f "python api.py" 2>/dev/null || true

# Stop Redis (optional - might be shared)
echo -e "${YELLOW}[3/3] Stopping Redis...${NC}"
if [ -f "$PID_DIR/redis.pid" ]; then
    stop_service "redis"
else
    echo -e "${YELLOW}  ⚠ Redis not managed by this script (may be system service)${NC}"
fi

echo ""
echo -e "${GREEN}  All services stopped.${NC}"
echo ""
