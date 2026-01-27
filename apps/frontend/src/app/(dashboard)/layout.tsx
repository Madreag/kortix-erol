import { dehydrate, HydrationBoundary } from '@tanstack/react-query';
import { getQueryClient } from '@/lib/query-client';
import { threadsQueryOptions, systemHealthOptions } from '@/lib/query-options';
import DashboardLayoutContent from '@/components/dashboard/layout-content';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default async function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  const queryClient = getQueryClient();

  // Prefetch critical data in parallel (non-blocking)
  // These run on the server and stream to client via ReactQueryStreamedHydration
  await Promise.all([
    queryClient.prefetchQuery(threadsQueryOptions(1, 20)),
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </HydrationBoundary>
  );
}
