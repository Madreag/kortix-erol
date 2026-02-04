import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';
import { threadsQueryOptions } from '@/lib/query-options';
import FilesContent from './files-content';

/**
 * Files Page - Server Component with SSR Prefetching
 * 
 * Performance optimizations:
 * 1. SSR prefetching: Threads are fetched on the server and dehydrated
 * 2. HydrationBoundary: Client receives pre-populated cache
 * 3. Skeleton loaders: Shown instantly while data hydrates
 * 4. Lazy sandbox status: Fetched after initial render
 */
export default async function FilesPage() {
  const queryClient = getQueryClient();
  
  // Prefetch threads on server - client will use this cached data
  await queryClient.prefetchQuery(threadsQueryOptions(1, 50));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <FilesContent />
    </HydrationBoundary>
  );
}
