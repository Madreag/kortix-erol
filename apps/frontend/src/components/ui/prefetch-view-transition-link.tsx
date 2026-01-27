'use client';

/**
 * PrefetchViewTransitionLink Component
 * 
 * Combines PrefetchLink and ViewTransitionLink functionality:
 * - Prefetches React Query data on hover/focus
 * - Uses View Transitions API for smooth navigation
 * - Falls back gracefully when either feature is unavailable
 */

import Link from 'next/link';
import { useQueryClient, type FetchQueryOptions } from '@tanstack/react-query';
import { useViewTransition } from '@/hooks/use-view-transition';
import { useCallback, useState, type ReactNode, type MouseEvent, type CSSProperties } from 'react';

interface PrefetchViewTransitionLinkProps {
  href: string;
  children: ReactNode;
  className?: string;
  prefetchQueries?: FetchQueryOptions[];
  prefetchDelay?: number;
  viewTransitionName?: string;
  onClick?: (e: MouseEvent<HTMLAnchorElement>) => void;
}

export function PrefetchViewTransitionLink({
  href,
  children,
  className,
  prefetchQueries = [],
  prefetchDelay = 100,
  viewTransitionName,
  onClick,
}: PrefetchViewTransitionLinkProps) {
  const queryClient = useQueryClient();
  const { navigate } = useViewTransition();
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

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    // Call custom onClick if provided
    if (onClick) {
      onClick(e);
      // If custom handler prevented default, respect that
      if (e.defaultPrevented) return;
    }

    // Allow cmd/ctrl+click for new tab
    if (e.metaKey || e.ctrlKey) return;
    
    e.preventDefault();
    navigate(href);
  };

  const style: CSSProperties | undefined = viewTransitionName 
    ? { viewTransitionName } as CSSProperties
    : undefined;

  return (
    <Link
      href={href}
      onClick={handleClick}
      onMouseEnter={handlePrefetch}
      onFocus={handlePrefetch}
      className={className}
      style={style}
      prefetch={true}
    >
      {children}
    </Link>
  );
}
