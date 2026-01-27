/**
 * V2 API Client for Litestar Backend
 * 
 * High-performance endpoints using Litestar + msgspec.
 * Falls back to V1 via resilient-client.ts if V2 is unavailable.
 */

import { createClient } from '@/lib/supabase/client';

const API_V2_URL = `${process.env.NEXT_PUBLIC_BACKEND_URL}/v2`;

export interface V2RequestOptions extends RequestInit {
  skipAuth?: boolean;
  timeout?: number;
}

export interface V2Error extends Error {
  status?: number;
  code?: string;
  details?: unknown;
}

async function getAuthToken(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token || null;
}

/**
 * Make a request to the V2 Litestar API.
 * Throws on non-2xx responses for proper error handling.
 */
export async function v2Fetch<T>(
  endpoint: string,
  options: V2RequestOptions = {}
): Promise<T> {
  const { skipAuth = false, timeout = 30000, ...fetchOptions } = options;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...fetchOptions.headers,
    };
    
    if (!skipAuth) {
      const token = await getAuthToken();
      if (token) {
        (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
      }
    }
    
    const response = await fetch(`${API_V2_URL}${endpoint}`, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Request failed' }));
      const error: V2Error = new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
      error.status = response.status;
      error.code = errorData.code;
      error.details = errorData;
      throw error;
    }
    
    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }
    
    return response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

// V2 API endpoints (Litestar - faster serialization via msgspec)
export const v2Api = {
  health: {
    check: () => v2Fetch<{ status: string; engine: string; version: string }>(
      '/health',
      { skipAuth: true }
    ),
    detailed: () => v2Fetch<{ status: string; components: Record<string, unknown> }>(
      '/health/detailed',
      { skipAuth: true }
    ),
  },
  
  // Thread endpoints (will be migrated in future imp2 phases)
  threads: {
    list: (page = 1, limit = 20) => 
      v2Fetch<{ threads: unknown[]; pagination: { page: number; limit: number; total: number; pages: number } }>(
        `/threads?page=${page}&limit=${limit}`
      ),
    get: (id: string) => v2Fetch<unknown>(`/threads/${id}`),
    create: (data: { title?: string; project_id?: string }) =>
      v2Fetch<unknown>('/threads', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { title?: string }) =>
      v2Fetch<unknown>(`/threads/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) =>
      v2Fetch<void>(`/threads/${id}`, { method: 'DELETE' }),
  },
  
  // Project endpoints (will be migrated in future imp2 phases)
  projects: {
    list: (page = 1, limit = 20) =>
      v2Fetch<{ projects: unknown[]; pagination: { page: number; limit: number; total: number; pages: number } }>(
        `/projects?page=${page}&limit=${limit}`
      ),
    get: (id: string) => v2Fetch<unknown>(`/projects/${id}`),
    create: (data: { name: string; description?: string }) =>
      v2Fetch<unknown>('/projects', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: string) =>
      v2Fetch<void>(`/projects/${id}`, { method: 'DELETE' }),
  },
  
  // Agent endpoints (will be migrated in future imp2 phases)
  agents: {
    list: () => v2Fetch<{ agents: unknown[] }>('/agents'),
    get: (id: string) => v2Fetch<unknown>(`/agents/${id}`),
  },
};

/**
 * Check if V2 API is available by calling the health endpoint.
 */
export async function isV2Available(): Promise<boolean> {
  try {
    const result = await v2Api.health.check();
    return result.status === 'healthy' && result.engine === 'litestar';
  } catch {
    return false;
  }
}
