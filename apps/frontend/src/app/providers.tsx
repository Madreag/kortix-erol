'use client';

import { useState } from 'react';
import { QueryClient, QueryClientProvider, isServer } from '@tanstack/react-query';
import { ReactQueryStreamedHydration } from '@tanstack/react-query-next-experimental';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { handleApiError } from '@/lib/error-handler';
import { isLocalMode } from '@/lib/config';
import { 
  AgentRunLimitError, 
  BillingError, 
  ProjectLimitError, 
  ThreadLimitError,
  AgentCountLimitError,
  TriggerLimitError,
  CustomWorkerLimitError,
  ModelAccessDeniedError
} from '@/lib/api/errors';

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 60 seconds
        gcTime: 5 * 60 * 1000, // 5 minutes
        structuralSharing: true,
        retry: (failureCount, error: any) => {
          if (error?.status >= 400 && error?.status < 500) return false;
          if (error?.status === 404) return false;
          return failureCount < 3;
        },
        refetchOnMount: false,
        refetchOnWindowFocus: false,
        refetchOnReconnect: 'always',
      },
      mutations: {
        retry: (failureCount, error: any) => {
          if (error?.status >= 400 && error?.status < 500) return false;
          return failureCount < 1;
        },
        onError: (error: any) => {
          if (error instanceof BillingError || 
              error instanceof AgentRunLimitError ||
              error instanceof ProjectLimitError ||
              error instanceof ThreadLimitError ||
              error instanceof AgentCountLimitError ||
              error instanceof TriggerLimitError ||
              error instanceof CustomWorkerLimitError ||
              error instanceof ModelAccessDeniedError) {
            return;
          }
          handleApiError(error, {
            operation: 'perform action',
            silent: false,
          });
        },
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (isServer) {
    // Server: always make a new query client
    return makeQueryClient();
  }
  // Browser: reuse client across renders
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(() => getQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <ReactQueryStreamedHydration>
        {children}
      </ReactQueryStreamedHydration>
      {isLocalMode() && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  );
}
