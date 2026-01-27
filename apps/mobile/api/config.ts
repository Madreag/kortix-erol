import { Platform } from 'react-native';
import { supabase } from './supabase';
import { ENV_MODE, EnvMode } from '@/lib/utils/env-config';
import { log } from '@/lib/logger';

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8000/v1';
const BACKEND_URL_V2 = process.env.EXPO_PUBLIC_BACKEND_URL_V2 || BACKEND_URL.replace('/v1', '/v2');

const FRONTEND_URL = process.env.EXPO_PUBLIC_FRONTEND_URL || '';

// V2 API configuration
const V2_CONFIG = {
  enabled: process.env.EXPO_PUBLIC_USE_V2_API !== 'false', // Enabled by default
  failureThreshold: 3,
  circuitResetMs: 30000,
};

// Circuit breaker state for V2 API
let v2FailureCount = 0;
let v2CircuitOpen = false;
let v2CircuitResetTimer: ReturnType<typeof setTimeout> | null = null;

export function getServerUrl(): string {
  let url = BACKEND_URL;

  if (Platform.OS === 'web') {
    log.log('📡 Using backend URL (web):', url);
    return url;
  }

  if (url.includes('localhost') || url.includes('127.0.0.1')) {
    const devHost = process.env.EXPO_PUBLIC_DEV_HOST || (
      Platform.OS === 'ios' ? 'localhost' : '10.0.2.2'
    );
    url = url.replace('localhost', devHost).replace('127.0.0.1', devHost);
    log.log('📡 Using backend URL (localhost):', url);
  } else {
    log.log('📡 Using backend URL:', url);
  }

  return url;
}

/**
 * Get the frontend URL based on environment
 * Used for auth redirects, sharing links, etc.
 *
 * Priority:
 * 1. EXPO_PUBLIC_FRONTEND_URL if set (explicit override)
 * 2. Infer from backend URL (if backend is production, frontend should be too)
 * 3. Environment-based defaults (staging by default for Expo apps)
 */
export function getFrontendUrl(): string {
  // If explicitly set, use that
  if (FRONTEND_URL) {
    return FRONTEND_URL.replace(/\/$/, ''); // Remove trailing slash
  }

  // Infer from backend URL - if backend is production, frontend should be too
  if (BACKEND_URL.includes('api.kortix.com') || BACKEND_URL.includes('api.suna.so')) {
    return 'https://kortix.com';
  }
  if (BACKEND_URL.includes('staging.api') || BACKEND_URL.includes('staging-api')) {
    return 'https://staging.kortix.com';
  }

  // Fall back to environment-based defaults
  switch (ENV_MODE) {
    case EnvMode.PRODUCTION:
      return 'https://kortix.com';
    case EnvMode.STAGING:
      return 'https://staging.kortix.com';
    case EnvMode.LOCAL:
    default:
      return 'http://localhost:3000';
  }
}

export const API_URL = getServerUrl();
export const FRONTEND_SHARE_URL = getFrontendUrl();

export async function getAuthToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

export async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getAuthToken();
  
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

/**
 * Get V2 API URL with platform-specific adjustments
 */
export function getServerUrlV2(): string {
  let url = BACKEND_URL_V2;

  if (Platform.OS === 'web') {
    return url;
  }

  if (url.includes('localhost') || url.includes('127.0.0.1')) {
    const devHost = process.env.EXPO_PUBLIC_DEV_HOST || (
      Platform.OS === 'ios' ? 'localhost' : '10.0.2.2'
    );
    url = url.replace('localhost', devHost).replace('127.0.0.1', devHost);
  }

  return url;
}

export const API_URL_V2 = getServerUrlV2();

/**
 * Check if V2 API should be used (circuit breaker logic)
 */
export function shouldUseV2(): boolean {
  return V2_CONFIG.enabled && !v2CircuitOpen;
}

/**
 * Record a V2 API failure and potentially open circuit breaker
 */
function recordV2Failure(): void {
  v2FailureCount++;
  log.log(`[Mobile API] V2 failure #${v2FailureCount}`);
  
  if (v2FailureCount >= V2_CONFIG.failureThreshold) {
    v2CircuitOpen = true;
    log.log('[Mobile API] V2 circuit breaker OPEN');
    
    // Reset after timeout
    if (v2CircuitResetTimer) clearTimeout(v2CircuitResetTimer);
    v2CircuitResetTimer = setTimeout(() => {
      v2CircuitOpen = false;
      v2FailureCount = 0;
      log.log('[Mobile API] V2 circuit breaker RESET');
    }, V2_CONFIG.circuitResetMs);
  }
}

/**
 * Record a V2 API success
 */
function recordV2Success(): void {
  v2FailureCount = 0;
}

/**
 * Make a resilient API request with V2→V1 fallback
 * 
 * @param endpoint - API endpoint path (e.g., '/threads')
 * @param options - Fetch options
 * @param preferV2 - Whether to prefer V2 API (default: true for high-traffic routes)
 */
export async function resilientFetch(
  endpoint: string,
  options?: RequestInit,
  preferV2: boolean = true,
): Promise<Response> {
  const headers = await getAuthHeaders();
  const mergedOptions: RequestInit = {
    ...options,
    headers: { ...headers, ...options?.headers },
  };

  // Try V2 first if enabled and circuit is closed
  if (preferV2 && shouldUseV2()) {
    try {
      const v2Url = `${API_URL_V2}${endpoint}`;
      log.log(`[Mobile API] Trying V2: ${v2Url}`);
      
      const response = await fetch(v2Url, mergedOptions);
      
      if (response.ok || response.status < 500) {
        recordV2Success();
        return response;
      }
      
      // Server error - count as failure
      throw new Error(`V2 server error: ${response.status}`);
    } catch (error) {
      recordV2Failure();
      log.log(`[Mobile API] V2 failed, falling back to V1: ${endpoint}`);
    }
  }

  // Fallback to V1
  const v1Url = `${API_URL}${endpoint}`;
  return fetch(v1Url, mergedOptions);
}

/**
 * High-traffic route helpers using V2 with fallback
 */
export const apiV2 = {
  threads: {
    list: (params?: { page?: number; limit?: number }) => {
      const query = params ? `?page=${params.page || 1}&limit=${params.limit || 20}` : '';
      return resilientFetch(`/threads${query}`);
    },
    get: (threadId: string) => resilientFetch(`/threads/${threadId}`),
    create: (data: { title?: string }) => 
      resilientFetch('/threads', { method: 'POST', body: JSON.stringify(data) }),
    delete: (threadId: string) => 
      resilientFetch(`/threads/${threadId}`, { method: 'DELETE' }),
  },
  projects: {
    list: () => resilientFetch('/projects'),
    get: (projectId: string) => resilientFetch(`/projects/${projectId}`),
  },
  agents: {
    list: () => resilientFetch('/agents'),
    get: (agentId: string) => resilientFetch(`/agents/${agentId}`),
  },
  health: {
    check: () => resilientFetch('/health', {}, true),
    detailed: () => resilientFetch('/health/detailed', {}, true),
  },
};
