/**
 * Optimistic Mutation Hook
 * 
 * Generic helper for creating mutations with optimistic updates.
 * Handles cancel, snapshot, update, rollback, and invalidation.
 */

import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';

interface OptimisticMutationOptions<TData, TVariables, TContext = TData> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  queryKey: QueryKey;
  optimisticUpdate: (oldData: TData | undefined, variables: TVariables) => TData;
  onSuccess?: (data: TData, variables: TVariables, context: TContext | undefined) => void;
  onError?: (error: Error, variables: TVariables, context: TContext | undefined) => void;
}

export function useOptimisticMutation<TData, TVariables, TContext = TData>({
  mutationFn,
  queryKey,
  optimisticUpdate,
  onSuccess,
  onError,
}: OptimisticMutationOptions<TData, TVariables, TContext>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey });

      // Snapshot the previous value
      const previousData = queryClient.getQueryData<TData>(queryKey);

      // Optimistically update to the new value
      queryClient.setQueryData<TData>(queryKey, (old) => 
        optimisticUpdate(old, variables)
      );

      // Return context with the previous value
      return previousData as unknown as TContext;
    },
    onError: (error, variables, context) => {
      // Rollback to the previous value on error
      queryClient.setQueryData(queryKey, context);
      onError?.(error as Error, variables, context);
    },
    onSettled: () => {
      // Always refetch after error or success
      queryClient.invalidateQueries({ queryKey });
    },
    onSuccess,
  });
}
