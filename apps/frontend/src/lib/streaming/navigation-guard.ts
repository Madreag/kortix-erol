/**
 * Navigation Guard: Stream Cleanup on Navigation
 * 
 * Manages active streams and ensures proper cleanup when:
 * - User navigates away (popstate)
 * - Page unloads
 * - Component unmounts
 */

// Interface for stream connections (works with both StreamConnection and ResilientStreamClient)
export interface StreamLike {
  destroy(): void;
  isConnected(): boolean;
}

interface ActiveStream {
  connection: StreamLike;
  threadId: string;
  createdAt: number;
}

class NavigationGuard {
  private activeStreams = new Map<string, ActiveStream>();
  private cleanupInProgress = false;
  private isInitialized = false;

  constructor() {
    if (typeof window !== 'undefined') {
      this.initialize();
    }
  }

  private initialize(): void {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // Listen for back/forward navigation
    window.addEventListener('popstate', this.handleNavigation);

    // Listen for page unload
    window.addEventListener('beforeunload', this.handleBeforeUnload);

    // Listen for visibility change (tab switch)
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  }

  private handleNavigation = (): void => {
    console.log('[NavigationGuard] Navigation detected, cleaning up streams');
    this.cleanupAll();
  };

  private handleBeforeUnload = (): void => {
    console.log('[NavigationGuard] Page unload detected, cleaning up streams');
    this.cleanupAllSync();
  };

  private handleVisibilityChange = (): void => {
    // Optional: pause/resume streams based on visibility
    // For now, we keep streams alive when tab is hidden
  };

  /**
   * Register an active stream for cleanup tracking.
   */
  registerStream(threadId: string, connection: StreamLike): void {
    // Clean up any existing stream for this thread
    const existing = this.activeStreams.get(threadId);
    if (existing) {
      console.log(`[NavigationGuard] Replacing existing stream for thread ${threadId}`);
      this.cleanupStream(threadId, existing.connection);
    }

    this.activeStreams.set(threadId, {
      connection,
      threadId,
      createdAt: Date.now(),
    });

    console.log(`[NavigationGuard] Registered stream for thread ${threadId}. Active: ${this.activeStreams.size}`);
  }

  /**
   * Unregister a stream (call when stream completes normally).
   */
  unregisterStream(threadId: string): void {
    this.activeStreams.delete(threadId);
    console.log(`[NavigationGuard] Unregistered stream for thread ${threadId}. Active: ${this.activeStreams.size}`);
  }

  /**
   * Clean up a specific stream.
   */
  private cleanupStream(threadId: string, connection: StreamLike): void {
    try {
      connection.destroy();
    } catch (error) {
      console.warn(`[NavigationGuard] Failed to cleanup stream for ${threadId}:`, error);
    }
    this.activeStreams.delete(threadId);
  }

  /**
   * Clean up all active streams (async version).
   */
  async cleanupAll(): Promise<void> {
    if (this.cleanupInProgress) return;
    this.cleanupInProgress = true;

    try {
      const cleanups = Array.from(this.activeStreams.entries()).map(
        ([threadId, stream]) => {
          return new Promise<void>((resolve) => {
            try {
              this.cleanupStream(threadId, stream.connection);
            } catch (e) {
              console.warn(`[NavigationGuard] Cleanup error for ${threadId}:`, e);
            }
            resolve();
          });
        }
      );
      await Promise.allSettled(cleanups);
    } finally {
      this.cleanupInProgress = false;
    }
  }

  /**
   * Synchronous cleanup for beforeunload.
   */
  private cleanupAllSync(): void {
    for (const [threadId, stream] of this.activeStreams.entries()) {
      try {
        stream.connection.destroy();
      } catch {
        // Ignore errors during sync cleanup
      }
    }
    this.activeStreams.clear();
  }

  /**
   * Get count of active streams.
   */
  getActiveCount(): number {
    return this.activeStreams.size;
  }

  /**
   * Get all active thread IDs.
   */
  getActiveThreadIds(): string[] {
    return Array.from(this.activeStreams.keys());
  }

  /**
   * Check if a thread has an active stream.
   */
  hasActiveStream(threadId: string): boolean {
    return this.activeStreams.has(threadId);
  }

  /**
   * Cleanup and destroy the guard.
   */
  destroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('popstate', this.handleNavigation);
      window.removeEventListener('beforeunload', this.handleBeforeUnload);
      document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    }
    this.cleanupAllSync();
    this.isInitialized = false;
  }
}

// Singleton instance
let navigationGuard: NavigationGuard | null = null;

export function getNavigationGuard(): NavigationGuard {
  if (typeof window === 'undefined') {
    // Return a no-op guard for SSR
    return {
      registerStream: () => {},
      unregisterStream: () => {},
      cleanupAll: async () => {},
      getActiveCount: () => 0,
      getActiveThreadIds: () => [],
      hasActiveStream: () => false,
      destroy: () => {},
    } as unknown as NavigationGuard;
  }

  if (!navigationGuard) {
    navigationGuard = new NavigationGuard();
  }
  return navigationGuard;
}

export type { NavigationGuard };
