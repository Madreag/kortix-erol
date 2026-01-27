#!/bin/bash
# ============================================
# Kortix Suna - Start Services (WSL)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/apps/frontend"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Kortix Suna - Starting Services${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if a service is running
is_running() {
    local pid_file="$PID_DIR/$1.pid"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check if port is in use
port_in_use() {
    local port=$1
    if command -v ss &> /dev/null; then
        ss -tuln | grep -q ":$port "
    elif command -v netstat &> /dev/null; then
        netstat -tuln | grep -q ":$port "
    else
        # Fallback: try to connect
        (echo > /dev/tcp/localhost/$port) 2>/dev/null
    fi
}

# ============================================
# 1. Start Redis
# ============================================
echo -e "${YELLOW}[1/3] Starting Redis...${NC}"

if port_in_use 6379; then
    echo -e "${GREEN}  ✓ Redis already running on port 6379${NC}"
else
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes --pidfile "$PID_DIR/redis.pid" \
            --logfile "$LOG_DIR/redis.log" 2>/dev/null
        sleep 1
        if port_in_use 6379; then
            echo -e "${GREEN}  ✓ Redis started${NC}"
        else
            echo -e "${RED}  ✗ Failed to start Redis${NC}"
            exit 1
        fi
    else
        echo -e "${RED}  ✗ Redis not installed. Run: sudo apt install redis-server${NC}"
        exit 1
    fi
fi

# ============================================
# 2. Start Backend
# ============================================
echo -e "${YELLOW}[2/3] Starting Backend...${NC}"

if is_running "backend"; then
    echo -e "${GREEN}  ✓ Backend already running${NC}"
elif port_in_use 8000; then
    echo -e "${YELLOW}  ⚠ Port 8000 in use by another process${NC}"
else
    cd "$BACKEND_DIR"
    
    # Check for .env file
    if [ ! -f ".env" ]; then
        echo -e "${RED}  ✗ backend/.env not found. Run: python scripts/setup_wsl.py${NC}"
        exit 1
    fi
    
    # Start backend
    nohup uv run python api.py > "$LOG_DIR/backend.log" 2>&1 &
    echo $! > "$PID_DIR/backend.pid"
    
    # Wait for startup
    echo -n "  Waiting for backend"
    for i in {1..30}; do
        if port_in_use 8000; then
            echo ""
            echo -e "${GREEN}  ✓ Backend started (http://localhost:8000)${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! port_in_use 8000; then
        echo ""
        echo -e "${RED}  ✗ Backend failed to start. Check logs/backend.log${NC}"
        exit 1
    fi
fi

# ============================================
# 3. Start Frontend
# ============================================
echo -e "${YELLOW}[3/3] Starting Frontend...${NC}"

if is_running "frontend"; then
    echo -e "${GREEN}  ✓ Frontend already running${NC}"
elif port_in_use 3000; then
    echo -e "${YELLOW}  ⚠ Port 3000 in use by another process${NC}"
else
    cd "$FRONTEND_DIR"
    
    # Check for .env.local file
    if [ ! -f ".env.local" ]; then
        echo -e "${RED}  ✗ apps/frontend/.env.local not found. Run: python scripts/setup_wsl.py${NC}"
        exit 1
    fi
    
    # Start frontend
    nohup pnpm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    echo $! > "$PID_DIR/frontend.pid"
    
    # Wait for startup
    echo -n "  Waiting for frontend"
    for i in {1..30}; do
        if port_in_use 3000; then
            echo ""
            echo -e "${GREEN}  ✓ Frontend started (http://localhost:3000)${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    if ! port_in_use 3000; then
        echo ""
        echo -e "${RED}  ✗ Frontend failed to start. Check logs/frontend.log${NC}"
        exit 1
    fi
fi

# ============================================
# Summary
# ============================================
# Get external IP if available
EXTERNAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  All services started!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "  Local Access:"
echo "    Frontend:  http://localhost:3000"
echo "    Backend:   http://localhost:8000"
echo ""
if [ -n "$EXTERNAL_IP" ]; then
echo "  External Access:"
echo "    Frontend:  http://$EXTERNAL_IP:3000"
echo "    Backend:   http://$EXTERNAL_IP:8000"
echo ""
fi
echo "  Dashboard: python dashboard.py"
echo "  Logs: $LOG_DIR/"
echo "  Stop: ./stop.sh"
echo ""
