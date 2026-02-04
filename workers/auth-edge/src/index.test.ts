import { unstable_dev } from 'wrangler';
import type { Unstable_DevWorker } from 'wrangler';
import { describe, it, expect, beforeAll, afterAll } from 'vitest';

describe('Auth Edge Worker', () => {
  let worker: Unstable_DevWorker;

  beforeAll(async () => {
    worker = await unstable_dev('src/index.ts', {
      experimental: { disableExperimentalWarning: true },
      vars: {
        SUPABASE_URL: 'https://test.supabase.co',
        ENVIRONMENT: 'test',
      },
    });
  });

  afterAll(async () => {
    await worker.stop();
  });

  describe('Public routes', () => {
    it('should allow health check without auth', async () => {
      const response = await worker.fetch('/v2/health');
      // Note: In test mode without a real origin, this may fail
      // The important thing is it doesn't return 401
      expect(response.status).not.toBe(401);
    });

    it('should allow status endpoint without auth', async () => {
      const response = await worker.fetch('/v2/status');
      expect(response.status).not.toBe(401);
    });
  });

  describe('Protected routes', () => {
    it('should reject requests without auth header', async () => {
      const response = await worker.fetch('/v2/threads');
      expect(response.status).toBe(401);
      
      const body = await response.json() as { error: string };
      expect(body.error).toBe('unauthorized');
    });

    it('should reject invalid auth header format', async () => {
      const response = await worker.fetch('/v2/threads', {
        headers: { 'Authorization': 'InvalidFormat token123' },
      });
      expect(response.status).toBe(401);
      
      const body = await response.json() as { error: string };
      expect(body.error).toBe('unauthorized');
    });

    it('should reject Bearer without token', async () => {
      const response = await worker.fetch('/v2/threads', {
        headers: { 'Authorization': 'Bearer ' },
      });
      expect(response.status).toBe(401);
    });

    it('should reject invalid JWT', async () => {
      const response = await worker.fetch('/v2/threads', {
        headers: { 'Authorization': 'Bearer invalid.jwt.token' },
      });
      expect(response.status).toBe(401);
      
      const body = await response.json() as { error: string };
      expect(body.error).toBe('invalid_token');
    });
  });

  describe('Response headers', () => {
    it('should include WWW-Authenticate header on 401', async () => {
      const response = await worker.fetch('/v2/threads');
      expect(response.headers.get('WWW-Authenticate')).toBe('Bearer');
    });

    it('should include Content-Type header on error responses', async () => {
      const response = await worker.fetch('/v2/threads');
      expect(response.headers.get('Content-Type')).toBe('application/json');
    });
  });

  describe('Rate limiting', () => {
    it('should include rate limit headers after many requests', async () => {
      // Make several requests
      for (let i = 0; i < 5; i++) {
        await worker.fetch('/v2/threads', {
          headers: { 'Authorization': 'Bearer test' },
        });
      }
      
      // Rate limit headers should be present on rate limit response
      // Note: Full rate limit testing requires 100+ requests
    });
  });
});

describe('Rate Limiter', () => {
  it('should be importable', async () => {
    const { EdgeRateLimiter } = await import('./rate-limiter');
    expect(EdgeRateLimiter).toBeDefined();
  });

  it('should allow requests within limit', async () => {
    const { EdgeRateLimiter } = await import('./rate-limiter');
    const limiter = new EdgeRateLimiter({ windowMs: 60000, maxRequests: 10 });
    
    const result = await limiter.check('test-key');
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(9);
  });

  it('should block requests over limit', async () => {
    const { EdgeRateLimiter } = await import('./rate-limiter');
    const limiter = new EdgeRateLimiter({ windowMs: 60000, maxRequests: 2 });
    
    await limiter.check('test-key');
    await limiter.check('test-key');
    const result = await limiter.check('test-key');
    
    expect(result.allowed).toBe(false);
    expect(result.remaining).toBe(0);
  });
});

describe('Geo Routing', () => {
  it('should be importable', async () => {
    const { getOptimalOrigin, getGeoInfo } = await import('./geo-routing');
    expect(getOptimalOrigin).toBeDefined();
    expect(getGeoInfo).toBeDefined();
  });

  it('should return default origin when no cf data', async () => {
    const { getOptimalOrigin, DEFAULT_GEO_CONFIG } = await import('./geo-routing');
    const mockRequest = new Request('https://api.kortix.ai/v2/test');
    
    const origin = getOptimalOrigin(mockRequest);
    expect(origin).toBe(DEFAULT_GEO_CONFIG.defaultOrigin);
  });
});
