'use client';

/**
 * PrefetchLink Component
 * 
 * A link that prefetches React Query data on hover/focus.
 * Provides instant navigation by warming the cache before click.
 */

import Link, { type LinkProps } from 'next/link';
import { useQueryClient, type FetchQueryOptions } from '@tanstack/react-query';
import { useCallback, useState, type ReactNode } from 'react';

interface PrefetchLinkProps extends Omit<LinkProps, 'href'> {
  href: string;
  children: ReactNode;
  className?: string;
  prefetchQueries?: FetchQueryOptions[];
  prefetchDelay?: number;
}

export function PrefetchLink({
  href,
  children,
  className,
  prefetchQueries = [],
  prefetchDelay = 100,
  ...linkProps
}: PrefetchLinkProps) {
  const queryClient = useQueryClient();
  const [hasPrefetched, setHasPrefetched] = useState(false);

  const handlePrefetch = useCallback(() => {
    if (hasPrefetched || prefetchQueries.length === 0) return;

    const timeoutId = setTimeout(() => {
      prefetchQueries.forEach((options) => {
        queryClient.prefetchQuery(options);
      });
      setHasPrefetched(true);
    }, prefetchDelay);

    return () => clearTimeout(timeoutId);
  }, [queryClient, prefetchQueries, hasPrefetched, prefetchDelay]);

  return (
    <Link
      href={href}
      className={className}
      onMouseEnter={handlePrefetch}
      onFocus={handlePrefetch}
      {...linkProps}
    >
      {children}
    </Link>
  );
}
