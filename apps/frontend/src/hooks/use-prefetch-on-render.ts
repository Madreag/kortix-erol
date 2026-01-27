'use client';

/**
 * usePrefetchOnRender Hook
 * 
 * Prefetches React Query data when a component renders.
 * Useful for warming cache on component mount.
 */

import { useEffect, useRef } from 'react';
import { useQueryClient, type FetchQueryOptions } from '@tanstack/react-query';

export function usePrefetchOnRender(queries: FetchQueryOptions[]) {
  const queryClient = useQueryClient();
  const hasPrefetched = useRef(false);

  useEffect(() => {
    if (hasPrefetched.current) return;
    
    queries.forEach((options) => {
      queryClient.prefetchQuery(options);
    });
    
    hasPrefetched.current = true;
  }, [queryClient, queries]);
}
