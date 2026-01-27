import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';
import { threadDetailOptions, threadMessagesOptions, projectDetailOptions } from '@/lib/query-options';

interface ThreadLayoutProps {
  children: React.ReactNode;
  params: Promise<{ threadId: string; projectId: string }>;
}

export default async function ThreadLayout({
  children,
  params,
}: ThreadLayoutProps) {
  const { threadId, projectId } = await params;
  const queryClient = getQueryClient();

  // Prefetch thread and project data in parallel
  await Promise.all([
    queryClient.prefetchQuery(threadDetailOptions(threadId)),
    queryClient.prefetchQuery(threadMessagesOptions(threadId)),
    queryClient.prefetchQuery(projectDetailOptions(projectId)),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {children}
    </HydrationBoundary>
  );
}
  