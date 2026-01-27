/**
 * Adaptive Throttle: FPS-aware Throttling
 * 
 * Monitors frame timings and adjusts throttle intervals
 * to maintain smooth 60fps rendering during streaming.
 */

export interface AdaptiveThrottleConfig {
  targetFps?: number;
  timingWindow?: number;
  defaultThrottle?: number;
  minThrottle?: number;
  maxThrottle?: number;
}

const DEFAULT_CONFIG: Required<AdaptiveThrottleConfig> = {
  targetFps: 60,
  timingWindow: 10,
  defaultThrottle: 50,
  minThrottle: 16, // ~60fps
  maxThrottle: 100,
};

export class AdaptiveThrottle {
  private frameTimings: number[] = [];
  private lastFrameTime: number | null = null;
  private config: Required<AdaptiveThrottleConfig>;
  private rafId: number | null = null;
  private isMonitoring = false;

  constructor(config: AdaptiveThrottleConfig = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Start monitoring frame timings.
   */
  startMonitoring(): void {
    if (this.isMonitoring || typeof window === 'undefined') return;
    this.isMonitoring = true;
    this.measureFrame();
  }

  /**
   * Stop monitoring frame timings.
   */
  stopMonitoring(): void {
    this.isMonitoring = false;
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  private measureFrame = (): void => {
    if (!this.isMonitoring) return;

    this.recordFrame();
    this.rafId = requestAnimationFrame(this.measureFrame);
  };

  /**
   * Record a frame timing.
   */
  recordFrame(): void {
    const now = performance.now();
    if (this.lastFrameTime !== null) {
      const frameDuration = now - this.lastFrameTime;
      this.frameTimings.push(frameDuration);
      
      // Keep only the last N timings
      if (this.frameTimings.length > this.config.timingWindow) {
        this.frameTimings.shift();
      }
    }
    this.lastFrameTime = now;
  }

  /**
   * Get the current recommended throttle interval.
   */
  getCurrentThrottle(): number {
    if (this.frameTimings.length < 2) {
      return this.config.defaultThrottle;
    }

    // Calculate average frame time
    const avgFrameTime = this.frameTimings.reduce((a, b) => a + b, 0) / this.frameTimings.length;
    const targetFrameTime = 1000 / this.config.targetFps; // 16.67ms for 60fps

    if (avgFrameTime > targetFrameTime * 1.5) {
      // Browser is struggling - increase throttle
      const ratio = avgFrameTime / targetFrameTime;
      return Math.min(this.config.maxThrottle, this.config.defaultThrottle * ratio);
    } else if (avgFrameTime < targetFrameTime * 0.8) {
      // Headroom available - decrease throttle
      const ratio = avgFrameTime / targetFrameTime;
      return Math.max(this.config.minThrottle, this.config.defaultThrottle * ratio);
    }

    return this.config.defaultThrottle;
  }

  /**
   * Check if we're meeting the FPS target.
   */
  isMeetingTarget(): boolean {
    if (this.frameTimings.length < 2) return true;

    const avgFrameTime = this.frameTimings.reduce((a, b) => a + b, 0) / this.frameTimings.length;
    const targetFrameTime = 1000 / this.config.targetFps;

    return avgFrameTime <= targetFrameTime * 1.1; // 10% tolerance
  }

  /**
   * Get current average FPS.
   */
  getCurrentFps(): number {
    if (this.frameTimings.length < 2) return this.config.targetFps;

    const avgFrameTime = this.frameTimings.reduce((a, b) => a + b, 0) / this.frameTimings.length;
    return 1000 / avgFrameTime;
  }

  /**
   * Get frame timing statistics.
   */
  getStats(): {
    avgFrameTime: number;
    minFrameTime: number;
    maxFrameTime: number;
    fps: number;
    isMeetingTarget: boolean;
    recommendedThrottle: number;
  } {
    if (this.frameTimings.length < 2) {
      return {
        avgFrameTime: 16.67,
        minFrameTime: 16.67,
        maxFrameTime: 16.67,
        fps: 60,
        isMeetingTarget: true,
        recommendedThrottle: this.config.defaultThrottle,
      };
    }

    const avgFrameTime = this.frameTimings.reduce((a, b) => a + b, 0) / this.frameTimings.length;
    const minFrameTime = Math.min(...this.frameTimings);
    const maxFrameTime = Math.max(...this.frameTimings);

    return {
      avgFrameTime,
      minFrameTime,
      maxFrameTime,
      fps: 1000 / avgFrameTime,
      isMeetingTarget: this.isMeetingTarget(),
      recommendedThrottle: this.getCurrentThrottle(),
    };
  }

  /**
   * Reset timing data.
   */
  reset(): void {
    this.frameTimings = [];
    this.lastFrameTime = null;
  }

  /**
   * Destroy and clean up.
   */
  destroy(): void {
    this.stopMonitoring();
    this.reset();
  }
}

/**
 * Create an adaptive throttle with default or custom config.
 */
export function createAdaptiveThrottle(config?: AdaptiveThrottleConfig): AdaptiveThrottle {
  return new AdaptiveThrottle(config);
}

// Singleton for global throttle monitoring
let globalThrottle: AdaptiveThrottle | null = null;

export function getGlobalThrottle(): AdaptiveThrottle {
  if (typeof window === 'undefined') {
    return new AdaptiveThrottle();
  }
  
  if (!globalThrottle) {
    globalThrottle = new AdaptiveThrottle();
  }
  return globalThrottle;
}
