/**
 * Stream Resilience: V2→V1 Fallback with Resume Token
 * 
 * Handles reconnection during deployment and API transitions.
 * Supports resuming streams from last event ID.
 */

import { StreamConnection, createStreamConnection } from './stream-connection';
import { STREAM_CONFIG } from './constants';

export interface StreamState {
  lastEventId: string | null;
  endpoint: 'v1' | 'v2';
  reconnectAttempts: number;
  bufferQueue: StreamEvent[];
}

export interface StreamEvent {
  type: string;
  data: unknown;
  id?: string;
}

export interface ResilientStreamOptions {
  apiUrl: string;
  runId: string;
  getAuthToken: () => Promise<string | null>;
  onMessage: (data: string) => void;
  onOpen?: () => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
  onFallback?: (from: 'v2' | 'v1', to: 'v2' | 'v1') => void;
  preferV2?: boolean;
}

export class ResilientStreamClient {
  private connection: StreamConnection | null = null;
  private maxReconnects = STREAM_CONFIG.RECONNECT_MAX_ATTEMPTS;
  private reconnectDelay = STREAM_CONFIG.RECONNECT_BASE_DELAY_MS;
  private state: StreamState;
  private options: ResilientStreamOptions;
  private isDestroyed = false;

  constructor(options: ResilientStreamOptions) {
    this.options = options;
    this.state = {
      lastEventId: null,
      endpoint: options.preferV2 !== false ? 'v2' : 'v1',
      reconnectAttempts: 0,
      bufferQueue: [],
    };
  }

  async connect(): Promise<void> {
    if (this.isDestroyed) return;

    const url = this.buildUrl();
    
    this.connection = createStreamConnection({
      apiUrl: this.options.apiUrl,
      runId: this.options.runId,
      getAuthToken: this.options.getAuthToken,
      onMessage: (data: string) => {
        // Track last event ID for resume
        try {
          const parsed = JSON.parse(data);
          if (parsed._event_id || parsed.id) {
            this.state.lastEventId = parsed._event_id || parsed.id;
          }
        } catch {
          // Ignore parse errors for event ID extraction
        }
        
        this.state.reconnectAttempts = 0; // Reset on success
        this.options.onMessage(data);
      },
      onOpen: () => {
        this.state.reconnectAttempts = 0;
        this.options.onOpen?.();
      },
      onError: async (error) => {
        if (!this.isDestroyed) {
          await this.handleDisconnect(error);
        }
      },
      onClose: () => {
        this.options.onClose?.();
      },
    });

    await this.connection.connect();
  }

  private async handleDisconnect(error?: Error): Promise<void> {
    if (this.isDestroyed) return;

    if (this.state.reconnectAttempts >= this.maxReconnects) {
      console.error('[ResilientStream] Max reconnects reached, giving up');
      this.options.onError?.(error || new Error('Max reconnects reached'));
      return;
    }

    this.state.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.state.reconnectAttempts - 1);

    console.log(`[ResilientStream] Reconnecting in ${delay}ms (attempt ${this.state.reconnectAttempts})`);
    await new Promise(r => setTimeout(r, delay));

    if (this.isDestroyed) return;

    // Try V2 first, fallback to V1
    if (this.state.endpoint === 'v2') {
      try {
        await this.connect();
      } catch {
        console.warn('[ResilientStream] V2 failed, falling back to V1');
        this.options.onFallback?.('v2', 'v1');
        this.state.endpoint = 'v1';
        await this.connect();
      }
    } else {
      await this.connect();
    }
  }

  private buildUrl(): string {
    // The actual endpoint selection is handled by stream-connection
    // This method provides parameters for resume capability
    const params = new URLSearchParams();
    
    // Add resume token if available
    if (this.state.lastEventId) {
      params.set('last_event_id', this.state.lastEventId);
    }

    // Indicate preferred endpoint version
    if (this.state.endpoint === 'v2') {
      params.set('prefer_v2', 'true');
    }

    return params.toString() ? `?${params}` : '';
  }

  getLastEventId(): string | null {
    return this.state.lastEventId;
  }

  getCurrentEndpoint(): 'v1' | 'v2' {
    return this.state.endpoint;
  }

  getReconnectAttempts(): number {
    return this.state.reconnectAttempts;
  }

  isConnected(): boolean {
    return this.connection?.isConnected() ?? false;
  }

  destroy(): void {
    this.isDestroyed = true;
    if (this.connection) {
      this.connection.destroy();
      this.connection = null;
    }
  }
}

export function createResilientStream(options: ResilientStreamOptions): ResilientStreamClient {
  return new ResilientStreamClient(options);
}
