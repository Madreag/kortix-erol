'use client';

/**
 * ViewTransitionLink Component
 * 
 * A link component that uses the View Transitions API for smooth navigation.
 * Falls back to standard Link behavior when API is not supported.
 */

import Link from 'next/link';
import { useViewTransition } from '@/hooks/use-view-transition';
import type { ReactNode, MouseEvent, CSSProperties } from 'react';

interface ViewTransitionLinkProps {
  href: string;
  children: ReactNode;
  className?: string;
  viewTransitionName?: string;
  prefetch?: boolean;
}

export function ViewTransitionLink({
  href,
  children,
  className,
  viewTransitionName,
  prefetch = true,
}: ViewTransitionLinkProps) {
  const { navigate } = useViewTransition();

  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
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
      className={className}
      style={style}
      prefetch={prefetch}
    >
      {children}
    </Link>
  );
}
