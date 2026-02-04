#!/bin/bash
# Deploy script for Kortix Auth Edge Worker
# Usage: ./deploy.sh [environment]
# Environments: dev, staging, production (default: production)

set -e

ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying Kortix Auth Edge Worker to ${ENVIRONMENT}..."

cd "$SCRIPT_DIR"

# Check if wrangler is available
if ! command -v wrangler &> /dev/null && ! npx wrangler --version &> /dev/null; then
    echo "❌ wrangler not found. Installing..."
    npm install -g wrangler
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run tests before deployment
echo "🧪 Running tests..."
npm test || {
    echo "❌ Tests failed. Aborting deployment."
    exit 1
}

# First-time setup reminder
echo ""
echo "📝 First-time setup reminders:"
echo "   1. Create KV namespace: wrangler kv:namespace create JWKS_CACHE"
echo "   2. Set secrets: wrangler secret put SUPABASE_URL"
echo "   3. Set secrets: wrangler secret put SUPABASE_JWT_SECRET"
echo ""

# Deploy based on environment
case $ENVIRONMENT in
    dev)
        echo "🔧 Deploying to development..."
        npx wrangler deploy --env dev
        HEALTH_URL="https://api.dev.kortix.ai/v2/health"
        ;;
    staging)
        echo "🔧 Deploying to staging..."
        npx wrangler deploy --env staging
        HEALTH_URL="https://api.staging.kortix.ai/v2/health"
        ;;
    production)
        echo "🔧 Deploying to production..."
        npx wrangler deploy --env production
        HEALTH_URL="https://api.kortix.ai/v2/health"
        ;;
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        echo "Usage: ./deploy.sh [dev|staging|production]"
        exit 1
        ;;
esac

# Verify deployment
echo ""
echo "✅ Verifying deployment..."
sleep 3

STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null || echo "000")

if [ "$STATUS" = "200" ]; then
    echo "🎉 Deployment verified! Health check passed."
else
    echo "⚠️  Health check returned status: $STATUS"
    echo "   This might be expected if the origin is not configured yet."
fi

echo ""
echo "📊 To view logs: npx wrangler tail --env $ENVIRONMENT"
echo "🔄 To rollback: npx wrangler rollback --env $ENVIRONMENT"
