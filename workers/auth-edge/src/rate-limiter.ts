interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetAt: number;
}

/**
 * In-memory rate limiter for edge (uses Cloudflare's built-in for production)
 * This is a fallback implementation when Cloudflare's native rate limiting is not available
 */
export class EdgeRateLimiter {
  private limits: Map<string, RateLimitEntry> = new Map();
  private config: RateLimitConfig;
  private cleanupInterval: number | null = null;

  constructor(config: RateLimitConfig) {
    this.config = config;
  }

  /**
   * Check if a request is allowed under the rate limit
   */
  async check(key: string): Promise<RateLimitResult> {
    const now = Date.now();
    const entry = this.limits.get(key);

    // Clean up expired entries
    if (entry && entry.resetAt < now) {
      this.limits.delete(key);
    }

    const current = this.limits.get(key);

    if (!current) {
      // First request in window
      this.limits.set(key, {
        count: 1,
        resetAt: now + this.config.windowMs,
      });
      return {
        allowed: true,
        remaining: this.config.maxRequests - 1,
        resetAt: now + this.config.windowMs,
      };
    }

    if (current.count >= this.config.maxRequests) {
      return {
        allowed: false,
        remaining: 0,
        resetAt: current.resetAt,
      };
    }

    current.count++;
    return {
      allowed: true,
      remaining: this.config.maxRequests - current.count,
      resetAt: current.resetAt,
    };
  }

  /**
   * Reset rate limit for a specific key
   */
  reset(key: string): void {
    this.limits.delete(key);
  }

  /**
   * Get current rate limit status for a key without incrementing
   */
  status(key: string): RateLimitResult {
    const now = Date.now();
    const entry = this.limits.get(key);

    if (!entry || entry.resetAt < now) {
      return {
        allowed: true,
        remaining: this.config.maxRequests,
        resetAt: now + this.config.windowMs,
      };
    }

    return {
      allowed: entry.count < this.config.maxRequests,
      remaining: Math.max(0, this.config.maxRequests - entry.count),
      resetAt: entry.resetAt,
    };
  }

  /**
   * Clean up expired entries (should be called periodically)
   */
  cleanup(): void {
    const now = Date.now();
    for (const [key, entry] of this.limits.entries()) {
      if (entry.resetAt < now) {
        this.limits.delete(key);
      }
    }
  }

  /**
   * Get the number of tracked keys (for monitoring)
   */
  size(): number {
    return this.limits.size;
  }
}

/**
 * Create a rate limiter with sensible defaults
 */
export function createRateLimiter(options?: Partial<RateLimitConfig>): EdgeRateLimiter {
  return new EdgeRateLimiter({
    windowMs: options?.windowMs ?? 60000, // 1 minute default
    maxRequests: options?.maxRequests ?? 100, // 100 requests default
  });
}

/**
 * Tiered rate limits for different user types
 */
export const RATE_LIMIT_TIERS = {
  anonymous: { windowMs: 60000, maxRequests: 20 },
  authenticated: { windowMs: 60000, maxRequests: 100 },
  premium: { windowMs: 60000, maxRequests: 500 },
  admin: { windowMs: 60000, maxRequests: 1000 },
} as const;

export type RateLimitTier = keyof typeof RATE_LIMIT_TIERS;

/**
 * Get the appropriate rate limit config for a user tier
 */
export function getRateLimitForTier(tier: RateLimitTier): RateLimitConfig {
  return RATE_LIMIT_TIERS[tier];
}
