#!/bin/bash
# Pre-warm dev server routes to eliminate first-visit compilation delay
# Run this after `pnpm dev` starts to pre-compile key routes

PORT="${1:-3000}"
BASE_URL="http://localhost:$PORT"

echo "🔥 Pre-warming dev server routes..."

# Wait for server to be ready
until curl -s "$BASE_URL" > /dev/null 2>&1; do
    echo "   Waiting for server at $BASE_URL..."
    sleep 1
done

# Pre-warm key routes in parallel
echo "   Compiling routes..."
(
    curl -s "$BASE_URL/" > /dev/null &
    curl -s "$BASE_URL/dashboard" > /dev/null &
    curl -s "$BASE_URL/auth/login" > /dev/null &
    curl -s "$BASE_URL/auth/signup" > /dev/null &
    wait
)

echo "✅ Routes pre-warmed! TTFB should now be faster."
