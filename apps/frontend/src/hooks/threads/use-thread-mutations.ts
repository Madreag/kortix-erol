'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  createThread, 
  addUserMessage 
} from '@/lib/api/threads';
import { toast } from '@/lib/toast';
import { handleApiError } from '@/lib/error-handler';
import { deleteThread } from './utils';
import { threadKeys } from './keys';
import { invalidateAccountState } from '@/hooks/billing/use-account-state';

export const useCreateThread = () => {
  return useMutation({
    mutationFn: ({ projectId }: { projectId: string }) => createThread(projectId),
    onSuccess: () => {
      toast.success('Thread created successfully');
    },
    onError: (error) => {
      handleApiError(error, {
        operation: 'create thread',
        resource: 'thread'
      });
    }
  });
};

export const useAddUserMessage = () => {
  return useMutation({
    mutationFn: ({ threadId, content }: { threadId: string; content: string }) => 
      addUserMessage(threadId, content),
    onError: (error) => {
      handleApiError(error, {
        operation: 'add message',
        resource: 'message'
      });
    }
  });
};

interface DeleteThreadVariables {
  threadId: string;
  sandboxId?: string;
  isNavigateAway?: boolean;
}

export const useDeleteThread = () => {
  const queryClient = useQueryClient();
  
  type ThreadsSnapshot = [readonly unknown[], unknown][];
  
  return useMutation<void, Error, DeleteThreadVariables, { previousThreads: ThreadsSnapshot }>({
    mutationFn: async ({ threadId, sandboxId }: DeleteThreadVariables) => {
      return await deleteThread(threadId, sandboxId);
    },
    onMutate: async ({ threadId }) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic update
      await queryClient.cancelQueries({ queryKey: threadKeys.lists() });
      
      // Snapshot current threads for rollback
      const previousThreads = queryClient.getQueriesData({ queryKey: threadKeys.lists() });
      
      // Optimistically remove thread from all cached thread lists
      queryClient.setQueriesData(
        { queryKey: threadKeys.lists() },
        (old: any) => {
          if (!old?.threads) return old;
          return {
            ...old,
            threads: old.threads.filter((t: any) => t.thread_id !== threadId),
            pagination: old.pagination ? {
              ...old.pagination,
              total: Math.max(0, (old.pagination.total || 0) - 1),
            } : old.pagination,
          };
        }
      );
      
      return { previousThreads };
    },
    onError: (_err, _variables, context) => {
      // Rollback to previous state on error
      if (context?.previousThreads) {
        for (const [queryKey, data] of context.previousThreads) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSuccess: () => {
      // Invalidate to ensure consistency (background refetch)
      queryClient.invalidateQueries({ queryKey: threadKeys.lists() });
      invalidateAccountState(queryClient, true, true);
    },
  });
};

interface DeleteMultipleThreadsVariables {
  threadIds: string[];
  threadSandboxMap?: Record<string, string>;
  onProgress?: (completed: number, total: number) => void;
}

export const useUpdateThread = () => {
  const queryClient = useQueryClient();
  
  type ThreadsSnapshot = [readonly unknown[], unknown][];
  
  return useMutation<
    void, 
    Error, 
    { threadId: string; data: { title?: string; is_public?: boolean } },
    { previousThreads: ThreadsSnapshot }
  >({
    mutationFn: async ({ threadId, data }) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/threads/${threadId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to update thread');
      }
    },
    onMutate: async ({ threadId, data }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: threadKeys.lists() });
      
      // Snapshot current threads for rollback
      const previousThreads = queryClient.getQueriesData({ queryKey: threadKeys.lists() });
      
      // Optimistically update thread in all cached lists
      queryClient.setQueriesData(
        { queryKey: threadKeys.lists() },
        (old: any) => {
          if (!old?.threads) return old;
          return {
            ...old,
            threads: old.threads.map((t: any) =>
              t.thread_id === threadId
                ? { ...t, ...data, updated_at: new Date().toISOString() }
                : t
            ),
          };
        }
      );
      
      // Also update detail cache if exists
      queryClient.setQueryData(
        threadKeys.details(threadId),
        (old: any) => old ? { ...old, ...data } : old
      );
      
      return { previousThreads };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousThreads) {
        for (const [queryKey, data] of context.previousThreads) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSuccess: (_data, { threadId }) => {
      // Invalidate to ensure consistency
      queryClient.invalidateQueries({ queryKey: threadKeys.lists() });
      queryClient.invalidateQueries({ queryKey: threadKeys.details(threadId) });
    },
  });
};

export const useDeleteMultipleThreads = () => {
  const queryClient = useQueryClient();
  
  type ThreadsSnapshot = [readonly unknown[], unknown][];
  
  return useMutation<
    { successful: string[]; failed: string[] }, 
    Error, 
    DeleteMultipleThreadsVariables,
    { previousThreads: ThreadsSnapshot }
  >({
    mutationFn: async ({ threadIds, threadSandboxMap, onProgress }: DeleteMultipleThreadsVariables) => {
      let completedCount = 0;
      const results = await Promise.all(
        threadIds.map(async (threadId) => {
          try {
            const sandboxId = threadSandboxMap?.[threadId];
            await deleteThread(threadId, sandboxId);
            completedCount++;
            onProgress?.(completedCount, threadIds.length);
            return { success: true, threadId };
          } catch (error) {
            return { success: false, threadId, error };
          }
        })
      );
      
      return {
        successful: results.filter(r => r.success).map(r => r.threadId),
        failed: results.filter(r => !r.success).map(r => r.threadId),
      };
    },
    onMutate: async ({ threadIds }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: threadKeys.lists() });
      
      // Snapshot for rollback
      const previousThreads = queryClient.getQueriesData({ queryKey: threadKeys.lists() });
      
      // Optimistically remove all threads from cache
      const threadIdSet = new Set(threadIds);
      queryClient.setQueriesData(
        { queryKey: threadKeys.lists() },
        (old: any) => {
          if (!old?.threads) return old;
          return {
            ...old,
            threads: old.threads.filter((t: any) => !threadIdSet.has(t.thread_id)),
            pagination: old.pagination ? {
              ...old.pagination,
              total: Math.max(0, (old.pagination.total || 0) - threadIds.length),
            } : old.pagination,
          };
        }
      );
      
      return { previousThreads };
    },
    onError: (_err, _variables, context) => {
      // Rollback on error
      if (context?.previousThreads) {
        for (const [queryKey, data] of context.previousThreads) {
          queryClient.setQueryData(queryKey, data);
        }
      }
    },
    onSuccess: async (data) => {
      // If some failed, restore just those threads by invalidating
      if (data.failed.length > 0) {
        await queryClient.invalidateQueries({ queryKey: threadKeys.lists() });
      }
      invalidateAccountState(queryClient, true, true);
    },
  });
};
