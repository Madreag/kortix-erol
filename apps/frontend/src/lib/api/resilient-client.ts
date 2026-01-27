/**
 * Resilient API Client with V2 → V1 Fallback
 * 
 * Implements circuit breaker pattern for graceful degradation.
 * Tries V2 (Litestar) first, falls back to V1 (FastAPI) on failure.
 */

import { backendApi } from '../api-client';
import { v2Fetch, type V2Error } from './v2-client';

interface FallbackOptions {
  preferV2?: boolean;
  retryOnV2Failure?: boolean;
  logFallback?: boolean;
}

const DEFAULT_OPTIONS: FallbackOptions = {
  preferV2: true,
  retryOnV2Failure: true,
  logFallback: process.env.NODE_ENV === 'development',
};

class ResilientApiClient {
  private v2FailureCount = 0;
  private v2CircuitOpen = false;
  private circuitResetTimeout: ReturnType<typeof setTimeout> | null = null;
  
  private readonly CIRCUIT_THRESHOLD = 5;  // Failures before opening circuit
  private readonly CIRCUIT_RESET_MS = 30000;  // 30 seconds
  
  /**
   * Fetch data with automatic V2 → V1 fallback.
   */
  async fetch<T>(
    path: string, 
    options?: RequestInit & FallbackOptions
  ): Promise<T> {
    const { preferV2, retryOnV2Failure, logFallback, ...fetchOptions } = {
      ...DEFAULT_OPTIONS,
      ...options,
    };
    
    // If circuit is open, skip V2 entirely
    if (this.v2CircuitOpen) {
      if (logFallback) {
        console.warn(`[API] V2 circuit open, using V1 for ${path}`);
      }
      return this.fetchV1<T>(path, fetchOptions);
    }
    
    // Try V2 first if preferred
    if (preferV2) {
      try {
        const result = await v2Fetch<T>(path, fetchOptions);
        this.resetFailureCount();
        return result;
      } catch (error) {
        this.recordV2Failure();
        
        // Only fallback on server/network errors, not 4xx client errors
        if (retryOnV2Failure && this.shouldFallback(error as V2Error)) {
          if (logFallback) {
            console.warn(`[API] V2 failed for ${path}, falling back to V1:`, (error as Error).message);
          }
          return this.fetchV1<T>(path, fetchOptions);
        }
        throw error;
      }
    }
    
    // Use V1 directly
    return this.fetchV1<T>(path, fetchOptions);
  }
  
  /**
   * Fetch from V1 API (FastAPI).
   */
  private async fetchV1<T>(path: string, options?: RequestInit): Promise<T> {
    const method = options?.method?.toUpperCase() || 'GET';
    let response;
    
    switch (method) {
      case 'POST':
        response = await backendApi.post<T>(path, options?.body ? JSON.parse(options.body as string) : undefined);
        break;
      case 'PUT':
        response = await backendApi.put<T>(path, options?.body ? JSON.parse(options.body as string) : undefined);
        break;
      case 'PATCH':
        response = await backendApi.patch<T>(path, options?.body ? JSON.parse(options.body as string) : undefined);
        break;
      case 'DELETE':
        response = await backendApi.delete<T>(path);
        break;
      default:
        response = await backendApi.get<T>(path);
    }
    
    if (response.error) {
      throw response.error;
    }
    
    return response.data as T;
  }
  
  /**
   * Determine if we should fall back to V1 based on error type.
   */
  private shouldFallback(error: V2Error): boolean {
    // Fallback on 5xx errors or network failures
    if (error.status && error.status >= 500) return true;
    if (error.name === 'NetworkError' || error.name === 'TypeError') return true;
    if (error.message?.includes('fetch')) return true;
    if (error.message?.includes('aborted')) return true;
    // Fallback on 404 for V2 endpoints that don't exist yet
    if (error.status === 404) return true;
    return false;
  }
  
  private recordV2Failure(): void {
    this.v2FailureCount++;
    if (this.v2FailureCount >= this.CIRCUIT_THRESHOLD) {
      this.openCircuit();
    }
  }
  
  private openCircuit(): void {
    this.v2CircuitOpen = true;
    console.error('[API] V2 circuit breaker OPEN - too many failures');
    
    // Auto-reset after timeout
    this.circuitResetTimeout = setTimeout(() => {
      this.v2CircuitOpen = false;
      this.v2FailureCount = 0;
      console.info('[API] V2 circuit breaker RESET - retrying V2');
    }, this.CIRCUIT_RESET_MS);
  }
  
  private resetFailureCount(): void {
    if (this.v2FailureCount > 0) {
      this.v2FailureCount = 0;
    }
  }
  
  /**
   * Get current circuit breaker status.
   */
  getCircuitStatus(): { isOpen: boolean; failureCount: number } {
    return {
      isOpen: this.v2CircuitOpen,
      failureCount: this.v2FailureCount,
    };
  }
  
  /**
   * Manually reset the circuit breaker.
   */
  resetCircuit(): void {
    if (this.circuitResetTimeout) {
      clearTimeout(this.circuitResetTimeout);
      this.circuitResetTimeout = null;
    }
    this.v2CircuitOpen = false;
    this.v2FailureCount = 0;
  }
}

// Singleton instance
export const resilientClient = new ResilientApiClient();

// Convenience export for direct use
export const apiClient = resilientClient;
