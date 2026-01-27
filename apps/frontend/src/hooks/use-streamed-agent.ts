/**
 * useStreamedAgent: Hook for Streamed Agent Responses
 * 
 * Provides a React Query-based hook for streaming AI agent responses
 * with derived state for text content, tool calls, and completion status.
 */

'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useCallback, useEffect, useRef } from 'react';
import { 
  agentStreamQueryOptions, 
  type StreamedMessage, 
  type StreamChunk 
} from '@/lib/query-options/streamed';

export interface UseStreamedAgentOptions {
  enabled?: boolean;
  onFirstToken?: () => void;
  onComplete?: (message: StreamedMessage) => void;
  onError?: (error: string) => void;
}

export interface UseStreamedAgentResult {
  /** Combined text content from all text chunks */
  textContent: string;
  /** Combined reasoning content */
  reasoningContent: string;
  /** Current tool call chunk (if any) */
  currentToolCall: StreamChunk | null;
  /** All tool call chunks */
  toolCalls: StreamChunk[];
  /** Whether the stream is actively fetching */
  isStreaming: boolean;
  /** Whether the stream has completed */
  isComplete: boolean;
  /** Error message if any */
  error: string | null;
  /** Total number of chunks received */
  chunkCount: number;
  /** Refetch/restart the stream */
  refetch: () => void;
  /** Cancel the current stream */
  cancel: () => void;
}

/**
 * Hook for streaming agent responses with TanStack Query.
 */
export function useStreamedAgent(
  threadId: string,
  messageId: string,
  options: UseStreamedAgentOptions = {}
): UseStreamedAgentResult {
  const queryClient = useQueryClient();
  const hasCalledFirstToken = useRef(false);
  const hasCalledComplete = useRef(false);

  // Get auth token function
  const getAuthToken = useCallback(async (): Promise<string | null> => {
    const { createClient } = await import('@/lib/supabase/client');
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  }, []);

  const query = useQuery({
    ...agentStreamQueryOptions(threadId, messageId, getAuthToken),
    enabled: options.enabled !== false && !!threadId && !!messageId,
  });

  // Derive text content from chunks
  const textContent = useMemo(() => {
    if (!query.data?.chunks) return '';
    return query.data.chunks
      .filter((c) => c.type === 'text')
      .sort((a, b) => a.sequence - b.sequence)
      .map((c) => c.content)
      .join('');
  }, [query.data?.chunks]);

  // Derive reasoning content from chunks
  const reasoningContent = useMemo(() => {
    if (!query.data?.chunks) return '';
    return query.data.chunks
      .filter((c) => c.type === 'reasoning')
      .sort((a, b) => a.sequence - b.sequence)
      .map((c) => c.content)
      .join('');
  }, [query.data?.chunks]);

  // Get all tool call chunks
  const toolCalls = useMemo(() => {
    if (!query.data?.chunks) return [];
    return query.data.chunks.filter((c) => c.type === 'tool_call');
  }, [query.data?.chunks]);

  // Get current (latest) tool call
  const currentToolCall = useMemo(() => {
    if (toolCalls.length === 0) return null;
    return toolCalls[toolCalls.length - 1];
  }, [toolCalls]);

  // Call onFirstToken when first text chunk arrives
  useEffect(() => {
    if (
      !hasCalledFirstToken.current &&
      query.data?.chunks &&
      query.data.chunks.some((c) => c.type === 'text')
    ) {
      hasCalledFirstToken.current = true;
      options.onFirstToken?.();
    }
  }, [query.data?.chunks, options]);

  // Call onComplete when stream finishes
  useEffect(() => {
    if (
      !hasCalledComplete.current &&
      query.data?.isComplete
    ) {
      hasCalledComplete.current = true;
      options.onComplete?.(query.data);
    }
  }, [query.data, options]);

  // Call onError when error occurs
  useEffect(() => {
    if (query.data?.error) {
      options.onError?.(query.data.error);
    }
  }, [query.data?.error, options]);

  // Reset flags when messageId changes
  useEffect(() => {
    hasCalledFirstToken.current = false;
    hasCalledComplete.current = false;
  }, [messageId]);

  // Cancel function
  const cancel = useCallback(() => {
    queryClient.cancelQueries({
      queryKey: ['agent-stream', threadId, messageId],
    });
  }, [queryClient, threadId, messageId]);

  // Refetch function
  const refetch = useCallback(() => {
    hasCalledFirstToken.current = false;
    hasCalledComplete.current = false;
    query.refetch();
  }, [query]);

  return {
    textContent,
    reasoningContent,
    currentToolCall,
    toolCalls,
    isStreaming: query.isFetching && !query.data?.isComplete,
    isComplete: query.data?.isComplete ?? false,
    error: query.data?.error ?? (query.error ? String(query.error) : null),
    chunkCount: query.data?.chunks?.length ?? 0,
    refetch,
    cancel,
  };
}

/**
 * Hook for prefetching a stream (warms the cache).
 */
export function usePrefetchStream() {
  const queryClient = useQueryClient();

  const getAuthToken = useCallback(async (): Promise<string | null> => {
    const { createClient } = await import('@/lib/supabase/client');
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token || null;
  }, []);

  return useCallback(
    (threadId: string, messageId: string) => {
      queryClient.prefetchQuery(
        agentStreamQueryOptions(threadId, messageId, getAuthToken)
      );
    },
    [queryClient, getAuthToken]
  );
}
