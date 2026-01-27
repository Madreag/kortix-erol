/**
 * Server-compatible Query Client Factory
 * 
 * This file can be imported from both server and client components.
 * For RSC prefetching, use getQueryClient() which creates a new client per request.
 */

import { QueryClient } from '@tanstack/react-query';
import { cache } from 'react';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 60 seconds
        gcTime: 5 * 60 * 1000, // 5 minutes
        refetchOnMount: false,
        refetchOnWindowFocus: false,
      },
    },
  });
}

// For server components: creates a new QueryClient per request (cached within the request)
// React's cache() ensures the same client is reused within a single request
export const getQueryClient = cache(() => makeQueryClient());
