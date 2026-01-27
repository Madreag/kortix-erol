/**
 * Specialized Mutation Helpers
 * 
 * Common mutation patterns for optimistic updates.
 */

import { useMutation, useQueryClient, type QueryKey } from '@tanstack/react-query';

/**
 * Optimistic toggle mutation for boolean fields
 */
export function useOptimisticToggle<TData extends { id: string }>(
  queryKey: QueryKey,
  mutationFn: (id: string, value: boolean) => Promise<TData>,
  setToggleField: (item: TData, value: boolean) => TData
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, value }: { id: string; value: boolean }) => mutationFn(id, value),
    onMutate: async ({ id, value }) => {
      await queryClient.cancelQueries({ queryKey });
      
      const previousData = queryClient.getQueryData<TData[]>(queryKey);
      
      queryClient.setQueryData<TData[]>(queryKey, (old) =>
        old?.map((item) =>
          item.id === id ? setToggleField(item, value) : item
        )
      );
      
      return { previousData };
    },
    onError: (_err, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousData);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * Optimistic delete mutation
 */
export function useOptimisticDelete<TData extends { id: string }>(
  queryKey: QueryKey,
  mutationFn: (id: string) => Promise<void>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => mutationFn(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey });
      
      const previousData = queryClient.getQueryData<TData[]>(queryKey);
      
      queryClient.setQueryData<TData[]>(queryKey, (old) =>
        old?.filter((item) => item.id !== id)
      );
      
      return { previousData };
    },
    onError: (_err, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousData);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * Optimistic update mutation
 */
export function useOptimisticUpdate<TData extends { id: string }>(
  queryKey: QueryKey,
  mutationFn: (id: string, data: Partial<TData>) => Promise<TData>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<TData> }) => mutationFn(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey });
      
      const previousData = queryClient.getQueryData<TData[]>(queryKey);
      
      queryClient.setQueryData<TData[]>(queryKey, (old) =>
        old?.map((item) =>
          item.id === id ? { ...item, ...data } : item
        )
      );
      
      return { previousData };
    },
    onError: (_err, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousData);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}

/**
 * Optimistic create mutation with temporary ID
 */
export function useOptimisticCreate<TData extends { id: string }, TVariables>(
  queryKey: QueryKey,
  mutationFn: (variables: TVariables) => Promise<TData>,
  createOptimistic: (variables: TVariables) => TData
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey });
      
      const previousData = queryClient.getQueryData<TData[]>(queryKey);
      const optimisticItem = createOptimistic(variables);
      
      queryClient.setQueryData<TData[]>(queryKey, (old) =>
        old ? [optimisticItem, ...old] : [optimisticItem]
      );
      
      return { previousData, optimisticItem };
    },
    onError: (_err, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previousData);
    },
    onSuccess: (newItem, _variables, context) => {
      // Replace optimistic item with real one
      queryClient.setQueryData<TData[]>(queryKey, (old) =>
        old?.map((item) =>
          item.id === context?.optimisticItem.id ? newItem : item
        )
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
