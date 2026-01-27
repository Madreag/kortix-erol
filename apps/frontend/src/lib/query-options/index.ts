/**
 * Query Options Factories
 * 
 * Centralized queryOptions for RSC prefetching and client-side queries.
 * Uses V2 API where available, with automatic V1 fallback.
 */

import { queryOptions } from '@tanstack/react-query';

// Import existing API functions (V1) - these are the stable APIs
import { 
  getThreadsPaginated, 
  getThread, 
  getMessages,
  getProject,
  getProjectThreads,
  type ThreadsResponse,
  type Thread,
  type Message,
  type Project,
} from '@/lib/api/threads';

// Import keys
import { 
  threadKeys, 
  projectKeys, 
  accountKeys, 
  agentKeys, 
  systemKeys,
  userKeys,
  billingKeys,
} from './keys';

// Re-export keys for convenience
export * from './keys';

// ============================================================================
// THREADS
// ============================================================================

export const threadsQueryOptions = (page = 1, limit = 20) =>
  queryOptions({
    queryKey: threadKeys.paginated(page, limit),
    queryFn: () => getThreadsPaginated(undefined, page, limit),
    staleTime: 5 * 60 * 1000,  // 5 minutes
    gcTime: 10 * 60 * 1000,    // 10 minutes
  });

export const threadsByProjectOptions = (projectId: string) =>
  queryOptions({
    queryKey: threadKeys.byProject(projectId),
    queryFn: () => getProjectThreads(projectId),
    staleTime: 2 * 60 * 1000,
    enabled: !!projectId,
  });

export const threadDetailOptions = (threadId: string) =>
  queryOptions({
    queryKey: threadKeys.details(threadId),
    queryFn: () => getThread(threadId),
    staleTime: 60 * 1000,
    enabled: !!threadId,
  });

export const threadMessagesOptions = (threadId: string) =>
  queryOptions({
    queryKey: threadKeys.messages(threadId),
    queryFn: () => getMessages(threadId),
    staleTime: 30 * 1000,
    enabled: !!threadId,
  });

// ============================================================================
// PROJECTS
// ============================================================================

export const projectDetailOptions = (projectId: string) =>
  queryOptions({
    queryKey: projectKeys.details(projectId),
    queryFn: () => getProject(projectId),
    staleTime: 2 * 60 * 1000,
    enabled: !!projectId,
  });

export const projectThreadsOptions = (projectId: string) =>
  queryOptions({
    queryKey: projectKeys.threads(projectId),
    queryFn: () => getProjectThreads(projectId),
    staleTime: 2 * 60 * 1000,
    enabled: !!projectId,
  });

// ============================================================================
// SYSTEM / HEALTH
// ============================================================================

export const systemHealthOptions = () =>
  queryOptions({
    queryKey: systemKeys.health,
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/health`);
      if (!response.ok) throw new Error('Health check failed');
      return response.json();
    },
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });

export const systemHealthV2Options = () =>
  queryOptions({
    queryKey: systemKeys.healthV2,
    queryFn: async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/v2/health`);
      if (!response.ok) throw new Error('V2 Health check failed');
      return response.json();
    },
    staleTime: 60 * 1000,
    gcTime: 5 * 60 * 1000,
  });
