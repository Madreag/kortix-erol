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

  // Fire-and-forget prefetch - DO NOT await to avoid blocking TTFB
  // Data will stream to client via ReactQueryStreamedHydration
  // Using void to explicitly indicate we're not awaiting
  void queryClient.prefetchQuery(threadsQueryOptions(1, 20));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <DashboardLayoutContent>{children}</DashboardLayoutContent>
    </HydrationBoundary>
  );
}
