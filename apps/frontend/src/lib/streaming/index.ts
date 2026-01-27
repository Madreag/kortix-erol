export * from './types';
export * from './constants';
export * from './utils';
export * from './tool-accumulator';
export * from './message-processor';
export * from './stream-connection';
export * from './stream-preconnect';
export { useAgentStream } from './use-agent-stream';
export type { 
  AgentStreamCallbacks, 
  UseAgentStreamOptions, 
  UseAgentStreamResult 
} from './use-agent-stream';

export { useSmoothStream } from './animations';

// imp5: Streaming Optimization modules
export { 
  ResilientStreamClient, 
  createResilientStream,
  type ResilientStreamOptions,
  type StreamState,
} from './stream-resilience';
export { getNavigationGuard, type NavigationGuard } from './navigation-guard';
export { ChunkProcessor, createChunkProcessor, type ChunkProcessorConfig } from './chunk-processor';
export { AdaptiveThrottle, createAdaptiveThrottle, getGlobalThrottle, type AdaptiveThrottleConfig } from './adaptive-throttle';
export { streamingMetrics, StreamingMetricsCollector, type StreamingMetrics, type StreamMetricsSummary } from './metrics';
