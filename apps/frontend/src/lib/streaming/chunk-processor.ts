/**
 * Chunk Processor: RAF-based Adaptive Batching
 * 
 * Batches incoming stream chunks and flushes using requestAnimationFrame
 * for smooth 60fps rendering without janky updates.
 */

type FlushCallback = (text: string, lastSequence: number) => void;

export interface ChunkProcessorConfig {
  minFlushInterval?: number;
  maxBatchSize?: number;
  idleFlushDelay?: number;
}

const DEFAULT_CONFIG: Required<ChunkProcessorConfig> = {
  minFlushInterval: 16, // ~60fps
  maxBatchSize: 50,
  idleFlushDelay: 50,
};

export class ChunkProcessor {
  private pendingChunks: Array<{ content: string; sequence: number }> = [];
  private rafId: number | null = null;
  private lastFlushTime = 0;
  private flushCallback: FlushCallback;
  private config: Required<ChunkProcessorConfig>;
  private idleTimeoutId: ReturnType<typeof setTimeout> | null = null;

  constructor(onFlush: FlushCallback, config: ChunkProcessorConfig = {}) {
    this.flushCallback = onFlush;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Add a chunk to the pending queue.
   */
  addChunk(content: string, sequence: number): void {
    this.pendingChunks.push({ content, sequence });
    this.scheduleFlush();
  }

  /**
   * Add multiple chunks at once.
   */
  addChunks(chunks: Array<{ content: string; sequence: number }>): void {
    this.pendingChunks.push(...chunks);
    this.scheduleFlush();
  }

  /**
   * Schedule a flush using requestAnimationFrame.
   */
  private scheduleFlush(): void {
    // Clear any idle timeout
    if (this.idleTimeoutId !== null) {
      clearTimeout(this.idleTimeoutId);
      this.idleTimeoutId = null;
    }

    if (this.rafId !== null) return;

    const now = performance.now();
    const timeSinceLastFlush = now - this.lastFlushTime;

    if (timeSinceLastFlush >= this.config.minFlushInterval) {
      // Enough time has passed - flush immediately on next frame
      this.rafId = requestAnimationFrame(() => {
        this.rafId = null;
        this.flush();
      });
    } else {
      // Schedule for next frame
      this.rafId = requestAnimationFrame(() => {
        this.rafId = null;
        this.flush();
      });
    }
  }

  /**
   * Schedule an idle flush for any remaining chunks.
   */
  private scheduleIdleFlush(): void {
    if (this.idleTimeoutId !== null) return;
    if (this.pendingChunks.length === 0) return;

    this.idleTimeoutId = setTimeout(() => {
      this.idleTimeoutId = null;
      if (this.pendingChunks.length > 0) {
        this.flush();
      }
    }, this.config.idleFlushDelay);
  }

  /**
   * Flush pending chunks to callback.
   */
  private flush(): void {
    if (this.pendingChunks.length === 0) return;

    this.lastFlushTime = performance.now();

    // Take up to maxBatchSize chunks
    const batch = this.pendingChunks.splice(0, this.config.maxBatchSize);

    // Sort by sequence to maintain order
    batch.sort((a, b) => a.sequence - b.sequence);

    // Concatenate text
    const text = batch.map(c => c.content).join('');
    const lastSequence = batch[batch.length - 1].sequence;

    // Callback with combined text
    this.flushCallback(text, lastSequence);

    // If more chunks remain, schedule another flush
    if (this.pendingChunks.length > 0) {
      this.scheduleFlush();
    } else {
      // Schedule idle flush for any stragglers
      this.scheduleIdleFlush();
    }
  }

  /**
   * Force flush any remaining chunks immediately.
   */
  forceFlush(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.idleTimeoutId !== null) {
      clearTimeout(this.idleTimeoutId);
      this.idleTimeoutId = null;
    }

    // Flush all remaining chunks
    while (this.pendingChunks.length > 0) {
      this.flush();
    }
  }

  /**
   * Clean up resources.
   */
  destroy(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.idleTimeoutId !== null) {
      clearTimeout(this.idleTimeoutId);
      this.idleTimeoutId = null;
    }
    this.pendingChunks = [];
  }

  /**
   * Get pending chunk count.
   */
  getPendingCount(): number {
    return this.pendingChunks.length;
  }

  /**
   * Check if there are pending chunks.
   */
  hasPending(): boolean {
    return this.pendingChunks.length > 0;
  }

  /**
   * Get time since last flush.
   */
  getTimeSinceLastFlush(): number {
    return performance.now() - this.lastFlushTime;
  }
}

/**
 * Create a chunk processor with default or custom config.
 */
export function createChunkProcessor(
  onFlush: FlushCallback,
  config?: ChunkProcessorConfig
): ChunkProcessor {
  return new ChunkProcessor(onFlush, config);
}
