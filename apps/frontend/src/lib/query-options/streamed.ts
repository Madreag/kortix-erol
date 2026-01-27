/**
 * Streamed Query Options: TanStack Query experimental_streamedQuery
 * 
 * Uses AsyncIterable to process SSE streams as chunks for AI responses.
 * This provides React Query integration for streaming data.
 */

import { queryOptions } from '@tanstack/react-query';

const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL || '';

export interface StreamChunk {
  type: 'text' | 'tool_call' | 'status' | 'reasoning' | 'error';
  content: string;
  sequence: number;
  metadata?: Record<string, unknown>;
}

export interface StreamedMessage {
  chunks: StreamChunk[];
  isComplete: boolean;
  textContent: string;
  error: string | null;
}

/**
 * Parse SSE data into StreamChunk format.
 */
function parseSSEToChunk(data: string, sequence: number): StreamChunk | null {
  try {
    const parsed = JSON.parse(data);
    
    // Handle different message types
    if (parsed.type === 'assistant' || parsed.type === 'text') {
      const content = typeof parsed.content === 'string' 
        ? parsed.content 
        : JSON.parse(parsed.content || '{}').content || '';
      return {
        type: 'text',
        content,
        sequence: parsed.sequence ?? sequence,
        metadata: parsed.metadata ? JSON.parse(parsed.metadata) : undefined,
      };
    }
    
    if (parsed.type === 'tool') {
      return {
        type: 'tool_call',
        content: parsed.content || '',
        sequence: parsed.sequence ?? sequence,
        metadata: parsed.metadata ? JSON.parse(parsed.metadata) : undefined,
      };
    }
    
    if (parsed.type === 'reasoning') {
      const content = typeof parsed.content === 'string'
        ? parsed.content
        : JSON.parse(parsed.content || '{}').reasoning_content || '';
      return {
        type: 'reasoning',
        content,
        sequence: parsed.sequence ?? sequence,
      };
    }
    
    if (parsed.type === 'status') {
      return {
        type: 'status',
        content: parsed.content || '',
        sequence: parsed.sequence ?? sequence,
      };
    }
    
    if (parsed.type === 'error') {
      return {
        type: 'error',
        content: parsed.content || parsed.message || 'Unknown error',
        sequence: parsed.sequence ?? sequence,
      };
    }
    
    return null;
  } catch {
    return null;
  }
}

/**
 * Create an async generator that reads SSE stream.
 */
async function* createSSEGenerator(
  url: string,
  token: string | null,
  signal: AbortSignal
): AsyncGenerator<StreamChunk, void, unknown> {
  const response = await fetch(url, {
    signal,
    headers: {
      'Accept': 'text/event-stream',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let sequence = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;

          const chunk = parseSSEToChunk(data, sequence++);
          if (chunk) {
            yield chunk;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Reducer function for accumulating stream chunks.
 */
function streamReducer(acc: StreamedMessage, chunk: StreamChunk): StreamedMessage {
  const newChunks = [...acc.chunks, chunk];
  
  // Build text content from text chunks
  const textContent = newChunks
    .filter(c => c.type === 'text')
    .sort((a, b) => a.sequence - b.sequence)
    .map(c => c.content)
    .join('');

  // Check for completion
  const isComplete = chunk.type === 'status' && 
    (chunk.content.includes('completed') || chunk.content.includes('stopped'));

  // Check for errors
  const errorChunk = newChunks.find(c => c.type === 'error');
  const error = errorChunk ? errorChunk.content : null;

  return {
    chunks: newChunks,
    isComplete,
    textContent,
    error,
  };
}

/**
 * Create a streamed query for AI agent responses.
 * 
 * Note: This uses a custom implementation since experimental_streamedQuery
 * may not be available in all TanStack Query versions.
 */
export function agentStreamQueryOptions(
  threadId: string, 
  messageId: string,
  getAuthToken: () => Promise<string | null>
) {
  return queryOptions({
    queryKey: ['agent-stream', threadId, messageId] as const,
    queryFn: async ({ signal }): Promise<StreamedMessage> => {
      const token = await getAuthToken();
      const url = `${API_URL}/api/stream/${threadId}/${messageId}`;
      
      const initialState: StreamedMessage = {
        chunks: [],
        isComplete: false,
        textContent: '',
        error: null,
      };

      let result = initialState;

      // Consume the stream and accumulate chunks
      for await (const chunk of createSSEGenerator(url, token, signal)) {
        result = streamReducer(result, chunk);
        
        // Early exit on error
        if (result.error) break;
      }

      return result;
    },
    // Don't cache streaming queries
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
  });
}

/**
 * Create query options for streaming with custom endpoint.
 */
export function createStreamQueryOptions(
  queryKey: readonly unknown[],
  streamUrl: string,
  getAuthToken: () => Promise<string | null>
) {
  return queryOptions({
    queryKey,
    queryFn: async ({ signal }): Promise<StreamedMessage> => {
      const token = await getAuthToken();
      
      const initialState: StreamedMessage = {
        chunks: [],
        isComplete: false,
        textContent: '',
        error: null,
      };

      let result = initialState;

      for await (const chunk of createSSEGenerator(streamUrl, token, signal)) {
        result = streamReducer(result, chunk);
        if (result.error) break;
      }

      return result;
    },
    staleTime: 0,
    gcTime: 5 * 60 * 1000,
  });
}

// Re-export StreamChunk with alias for convenience
export type { StreamChunk as StreamedChunk };
