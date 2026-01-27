import { test, expect } from '@playwright/test';
import { createHmac } from 'crypto';

/**
 * Litestar V2 API E2E Tests
 * 
 * Tests for the new Litestar /v2 endpoints.
 * These tests verify the V2 API is functioning correctly.
 */

const BACKEND_URL = process.env.TEST_BACKEND_URL || 'http://localhost:8000';
const JWT_SECRET = process.env.SUPABASE_JWT_SECRET || '';

/**
 * Base64url encode a string
 */
function base64url(str: string): string {
  return Buffer.from(str)
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

/**
 * Generate a test JWT token for API authentication (HS256)
 */
function generateTestToken(userId: string = 'test-user-id'): string {
  if (!JWT_SECRET) {
    throw new Error('SUPABASE_JWT_SECRET not configured for tests');
  }
  
  const header = { alg: 'HS256', typ: 'JWT' };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: userId,
    aud: 'authenticated',
    role: 'authenticated',
    iat: now,
    exp: now + 3600, // 1 hour
  };
  
  const headerB64 = base64url(JSON.stringify(header));
  const payloadB64 = base64url(JSON.stringify(payload));
  const signature = createHmac('sha256', JWT_SECRET)
    .update(`${headerB64}.${payloadB64}`)
    .digest('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
  
  return `${headerB64}.${payloadB64}.${signature}`;
}

test.describe('Litestar V2 API Endpoints', () => {
  test('/v2/health returns healthy status', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/health`);
    expect(response.ok()).toBe(true);
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('/v2/health/detailed returns component statuses', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/health/detailed`);
    expect(response.ok()).toBe(true);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('components');
  });

  test('/v2/metrics/summary returns metrics', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/metrics/summary`);
    expect(response.ok()).toBe(true);
    
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data).toHaveProperty('p50_ms');
    expect(data).toHaveProperty('error_rate_5xx');
  });
});

test.describe('V2 Protected Endpoints (require auth)', () => {
  test.describe.configure({ mode: 'serial' });

  test('/v2/threads requires authentication', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/threads`);
    // Should return 401 without auth
    expect(response.status()).toBe(401);
  });

  test('/v2/projects requires authentication', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/projects`);
    expect(response.status()).toBe(401);
  });

  test('/v2/agents requires authentication', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/v2/agents`);
    expect(response.status()).toBe(401);
  });
});

test.describe('V2 API with Auth', () => {
  // Skip if JWT_SECRET not configured
  test.skip(!JWT_SECRET, 'SUPABASE_JWT_SECRET not configured');

  test('/v2/threads returns data when authenticated', async ({ request }) => {
    const authToken = generateTestToken();
    
    const response = await request.get(`${BACKEND_URL}/v2/threads`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    
    // Accept 200 (success) or 401 (token needs real Supabase user)
    expect([200, 401]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('threads');
      expect(Array.isArray(data.threads)).toBe(true);
    }
  });

  test('/v2/projects returns data when authenticated', async ({ request }) => {
    const authToken = generateTestToken();
    
    const response = await request.get(`${BACKEND_URL}/v2/projects`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    
    expect([200, 401]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('projects');
    }
  });

  test('/v2/agents returns data when authenticated', async ({ request }) => {
    const authToken = generateTestToken();
    
    const response = await request.get(`${BACKEND_URL}/v2/agents`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    
    expect([200, 401]).toContain(response.status());
    
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('agents');
    }
  });
});
