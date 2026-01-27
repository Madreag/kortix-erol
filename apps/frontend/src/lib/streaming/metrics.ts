/**
 * Streaming Metrics: TTFT, Token Count, Performance Tracking
 * 
 * Collects and reports streaming performance metrics
 * for monitoring and optimization.
 */

export interface StreamingMetrics {
  timeToFirstToken: number[];
  totalStreamTime: number[];
  tokenCount: number[];
  reconnections: number;
  errors: number;
}

export interface CurrentStreamMetrics {
  startTime: number;
  firstTokenTime: number | null;
  tokenCount: number;
  chunkCount: number;
  lastChunkTime: number;
}

export interface StreamMetricsSummary {
  avgTimeToFirstToken: number;
  avgStreamTime: number;
  avgTokenCount: number;
  avgTokensPerSecond: number;
  p50TimeToFirstToken: number;
  p95TimeToFirstToken: number;
  reconnections: number;
  errors: number;
  totalStreams: number;
}

class StreamingMetricsCollector {
  private metrics: StreamingMetrics = {
    timeToFirstToken: [],
    totalStreamTime: [],
    tokenCount: [],
    reconnections: 0,
    errors: 0,
  };

  private currentStream: CurrentStreamMetrics | null = null;
  private maxHistorySize = 100; // Keep last 100 stream metrics

  /**
   * Called when a new stream starts.
   */
  onStreamStart(): void {
    this.currentStream = {
      startTime: performance.now(),
      firstTokenTime: null,
      tokenCount: 0,
      chunkCount: 0,
      lastChunkTime: performance.now(),
    };
  }

  /**
   * Called when the first token is received.
   */
  onFirstToken(): void {
    if (this.currentStream && !this.currentStream.firstTokenTime) {
      this.currentStream.firstTokenTime = performance.now();
      const ttft = this.currentStream.firstTokenTime - this.currentStream.startTime;
      
      this.addToHistory(this.metrics.timeToFirstToken, ttft);
      this.reportMetric('time_to_first_token', ttft);

      // Log warning if TTFT exceeds target
      if (ttft > 200) {
        console.warn(`[StreamingMetrics] TTFT exceeded target: ${ttft.toFixed(0)}ms (target: <200ms)`);
      }
    }
  }

  /**
   * Called for each token/chunk received.
   */
  onToken(tokenCount: number = 1): void {
    if (this.currentStream) {
      this.currentStream.tokenCount += tokenCount;
      this.currentStream.chunkCount++;
      this.currentStream.lastChunkTime = performance.now();
    }
  }

  /**
   * Called when the stream ends.
   */
  onStreamEnd(): void {
    if (this.currentStream) {
      const totalTime = performance.now() - this.currentStream.startTime;
      const tokenCount = this.currentStream.tokenCount;

      this.addToHistory(this.metrics.totalStreamTime, totalTime);
      this.addToHistory(this.metrics.tokenCount, tokenCount);

      const tokensPerSecond = tokenCount / (totalTime / 1000);

      this.reportMetric('stream_duration', totalTime);
      this.reportMetric('token_count', tokenCount);
      this.reportMetric('tokens_per_second', tokensPerSecond);

      // Log performance summary
      if (process.env.NODE_ENV === 'development') {
        console.log(`[StreamingMetrics] Stream complete:`, {
          duration: `${totalTime.toFixed(0)}ms`,
          tokens: tokenCount,
          tokensPerSecond: tokensPerSecond.toFixed(1),
          ttft: this.currentStream.firstTokenTime
            ? `${(this.currentStream.firstTokenTime - this.currentStream.startTime).toFixed(0)}ms`
            : 'N/A',
        });
      }

      this.currentStream = null;
    }
  }

  /**
   * Called when a stream reconnects.
   */
  onReconnection(): void {
    this.metrics.reconnections++;
    this.reportMetric('stream_reconnection', 1);
  }

  /**
   * Called when a stream error occurs.
   */
  onError(errorType?: string): void {
    this.metrics.errors++;
    this.reportMetric('stream_error', 1, { error_type: errorType });
  }

  /**
   * Get current stream metrics (for in-progress streams).
   */
  getCurrentStreamMetrics(): CurrentStreamMetrics | null {
    return this.currentStream;
  }

  /**
   * Get time since stream started.
   */
  getElapsedTime(): number {
    if (!this.currentStream) return 0;
    return performance.now() - this.currentStream.startTime;
  }

  /**
   * Get current tokens per second rate.
   */
  getCurrentRate(): number {
    if (!this.currentStream) return 0;
    const elapsed = this.getElapsedTime();
    if (elapsed === 0) return 0;
    return this.currentStream.tokenCount / (elapsed / 1000);
  }

  private addToHistory(arr: number[], value: number): void {
    arr.push(value);
    if (arr.length > this.maxHistorySize) {
      arr.shift();
    }
  }

  private reportMetric(name: string, value: number, extra?: Record<string, unknown>): void {
    // Log in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[StreamingMetrics] ${name}: ${value.toFixed(2)}`, extra || '');
    }

    // Send to analytics (PostHog, if available)
    if (typeof window !== 'undefined' && (window as Record<string, unknown>).posthog) {
      const posthog = (window as Record<string, unknown>).posthog as {
        capture: (event: string, properties?: Record<string, unknown>) => void;
      };
      posthog.capture('streaming_metric', {
        metric_name: name,
        metric_value: value,
        ...extra,
      });
    }
  }

  private percentile(arr: number[], p: number): number {
    if (arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  private avg(arr: number[]): number {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
  }

  /**
   * Get aggregated metrics summary.
   */
  getSummary(): StreamMetricsSummary {
    return {
      avgTimeToFirstToken: this.avg(this.metrics.timeToFirstToken),
      avgStreamTime: this.avg(this.metrics.totalStreamTime),
      avgTokenCount: this.avg(this.metrics.tokenCount),
      avgTokensPerSecond: this.metrics.totalStreamTime.length > 0
        ? this.avg(this.metrics.tokenCount) / (this.avg(this.metrics.totalStreamTime) / 1000)
        : 0,
      p50TimeToFirstToken: this.percentile(this.metrics.timeToFirstToken, 50),
      p95TimeToFirstToken: this.percentile(this.metrics.timeToFirstToken, 95),
      reconnections: this.metrics.reconnections,
      errors: this.metrics.errors,
      totalStreams: this.metrics.totalStreamTime.length,
    };
  }

  /**
   * Reset all metrics.
   */
  reset(): void {
    this.metrics = {
      timeToFirstToken: [],
      totalStreamTime: [],
      tokenCount: [],
      reconnections: 0,
      errors: 0,
    };
    this.currentStream = null;
  }

  /**
   * Check if TTFT target is being met.
   */
  isMeetingTtftTarget(targetMs: number = 200): boolean {
    if (this.metrics.timeToFirstToken.length === 0) return true;
    return this.percentile(this.metrics.timeToFirstToken, 95) <= targetMs;
  }
}

// Singleton instance
export const streamingMetrics = new StreamingMetricsCollector();

// Export class for testing
export { StreamingMetricsCollector };
