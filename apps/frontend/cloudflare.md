# Cloudflare Configuration for Kortix

## DNS Settings
- Proxy status: Proxied (orange cloud)
- SSL/TLS: Full (strict)

## Speed Settings
- HTTP/3 (with QUIC): Enabled
- 0-RTT Connection Resumption: Enabled
- Early Hints: Enabled
- Rocket Loader: OFF (conflicts with React)

## Caching Settings
- Caching Level: Standard
- Browser Cache TTL: Respect Existing Headers

## Cache Rules (create in Cloudflare Dashboard)

### Rule 1: Static Assets
- When: URI Path matches `.*\.(js|css|woff2|png|jpg|svg|ico|webp|avif)$`
- Then:
  - Edge TTL: 1 year (31536000)
  - Browser TTL: 30 days (2592000)

### Rule 2: API GET Requests
- When: URI Path starts with `/api/` AND Request Method equals `GET`
- Then:
  - Edge TTL: 60 seconds
  - Cache Key: Include query string, include Authorization header

### Rule 3: Streaming Bypass
- When: URI Path contains `/stream` OR URI Path contains `/sse`
- Then:
  - Bypass cache

### Rule 4: HTML Pages
- When: Content-Type contains `text/html`
- Then:
  - Edge TTL: 60 seconds
  - Browser TTL: 0 (no-cache)

## Security Settings
- WAF: Enabled (Cloudflare Managed Ruleset)
- Bot Fight Mode: Enabled
- Challenge Passage: 30 minutes

## Performance Expectations

| Metric | Before | After Cloudflare |
|--------|--------|------------------|
| Global TTFB | 200-500ms | <100ms (edge cached) |
| Static asset load | 500-1500ms | <200ms |
| Edge cache hit rate | 0% | >70% |
