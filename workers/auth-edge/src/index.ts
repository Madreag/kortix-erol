import { jwtVerify, createRemoteJWKSet } from 'jose';

interface Env {
  SUPABASE_URL: string;
  SUPABASE_JWT_SECRET: string;
  JWKS_CACHE: KVNamespace;
  ENVIRONMENT: string;
}

// JWKS cache (module-level for warm workers)
let jwksCache: ReturnType<typeof createRemoteJWKSet> | null = null;
let jwksCacheTime = 0;
const JWKS_CACHE_TTL = 3600000; // 1 hour

// Public routes that don't require authentication
const PUBLIC_ROUTES = new Set([
  '/v2/health',
  '/v2/health/detailed',
  '/v2/status',
]);

// Routes that bypass rate limiting
const RATE_LIMIT_BYPASS = new Set([
  '/v2/health',
  '/v2/stream',
]);

// In-memory rate limit tracking (per isolate)
const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX = 100; // requests per window

function checkRateLimit(clientId: string): { allowed: boolean; remaining: number } {
  const now = Date.now();
  const entry = rateLimitMap.get(clientId);

  // Clean expired entries
  if (entry && entry.resetAt < now) {
    rateLimitMap.delete(clientId);
  }

  const current = rateLimitMap.get(clientId);

  if (!current) {
    rateLimitMap.set(clientId, { count: 1, resetAt: now + RATE_LIMIT_WINDOW });
    return { allowed: true, remaining: RATE_LIMIT_MAX - 1 };
  }

  if (current.count >= RATE_LIMIT_MAX) {
    return { allowed: false, remaining: 0 };
  }

  current.count++;
  return { allowed: true, remaining: RATE_LIMIT_MAX - current.count };
}

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const startTime = performance.now();
    const url = new URL(request.url);
    const path = url.pathname;

    // Skip auth for public routes
    if (PUBLIC_ROUTES.has(path)) {
      return fetch(request);
    }

    // Get client identifier for rate limiting
    const clientIP = request.headers.get('CF-Connecting-IP') || 'unknown';
    const clientId = request.headers.get('X-Client-ID') || clientIP;

    // Rate limiting (skip for certain routes)
    if (!RATE_LIMIT_BYPASS.has(path)) {
      const { allowed, remaining } = checkRateLimit(clientId);
      if (!allowed) {
        return new Response(JSON.stringify({
          error: 'rate_limit_exceeded',
          message: 'Too many requests. Please try again later.',
          retry_after: 60,
        }), {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': '60',
            'X-RateLimit-Limit': String(RATE_LIMIT_MAX),
            'X-RateLimit-Remaining': '0',
          },
        });
      }
    }

    // Extract and validate JWT
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return new Response(JSON.stringify({
        error: 'unauthorized',
        message: 'Missing or invalid Authorization header',
      }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
          'WWW-Authenticate': 'Bearer',
        },
      });
    }

    const token = authHeader.slice(7);

    try {
      // Get or create JWKS
      const jwks = await getJWKS(env, ctx);
      
      // Verify JWT
      const { payload } = await jwtVerify(token, jwks, {
        issuer: `${env.SUPABASE_URL}/auth/v1`,
        audience: 'authenticated',
      });

      // Check token expiration with grace period
      const now = Math.floor(Date.now() / 1000);
      if (payload.exp && payload.exp < now - 30) {
        return new Response(JSON.stringify({
          error: 'token_expired',
          message: 'Token has expired',
        }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      // Create modified request with user info
      const modifiedHeaders = new Headers(request.headers);
      modifiedHeaders.set('X-User-ID', payload.sub as string);
      modifiedHeaders.set('X-User-Email', (payload.email as string) || '');
      modifiedHeaders.set('X-User-Role', (payload.role as string) || 'authenticated');
      modifiedHeaders.set('X-Auth-Verified', 'true');
      modifiedHeaders.set('X-Auth-Verified-At', new Date().toISOString());

      // Add user metadata if available
      if (payload.user_metadata) {
        modifiedHeaders.set('X-User-Metadata', JSON.stringify(payload.user_metadata));
      }

      // Forward to origin
      const modifiedRequest = new Request(request, {
        headers: modifiedHeaders,
      });

      const response = await fetch(modifiedRequest);

      // Add edge timing header
      const authTime = performance.now() - startTime;
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('X-Edge-Auth-Time', `${authTime.toFixed(2)}ms`);
      responseHeaders.set('X-Edge-Location', (request.cf?.colo as string) || 'unknown');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });

    } catch (error) {
      console.error('JWT verification failed:', error);
      
      // Determine error type
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const isExpired = errorMessage.includes('expired');
      const isInvalid = errorMessage.includes('invalid') || errorMessage.includes('malformed');

      return new Response(JSON.stringify({
        error: isExpired ? 'token_expired' : isInvalid ? 'invalid_token' : 'auth_error',
        message: isExpired ? 'Token has expired' : 'Invalid authentication token',
      }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};

/**
 * Get or create JWKS with caching
 */
async function getJWKS(env: Env, ctx: ExecutionContext) {
  const now = Date.now();
  
  // Return cached JWKS if still valid
  if (jwksCache && now - jwksCacheTime < JWKS_CACHE_TTL) {
    return jwksCache;
  }

  // Try to get from KV cache first
  try {
    const cachedJwks = await env.JWKS_CACHE.get('jwks', 'json') as { timestamp: number } | null;
    if (cachedJwks && now - cachedJwks.timestamp < JWKS_CACHE_TTL) {
      jwksCache = createRemoteJWKSet(new URL(`${env.SUPABASE_URL}/auth/v1/.well-known/jwks.json`));
      jwksCacheTime = now;
      return jwksCache;
    }
  } catch (e) {
    // KV might not be configured, continue without it
    console.warn('KV cache not available:', e);
  }

  // Fetch fresh JWKS
  jwksCache = createRemoteJWKSet(
    new URL(`${env.SUPABASE_URL}/auth/v1/.well-known/jwks.json`)
  );
  jwksCacheTime = now;

  // Update KV cache in background
  ctx.waitUntil(
    (async () => {
      try {
        await env.JWKS_CACHE.put('jwks', JSON.stringify({ timestamp: now }), {
          expirationTtl: 3600,
        });
      } catch (e) {
        console.warn('Failed to update KV cache:', e);
      }
    })()
  );

  return jwksCache;
}
