'use client';

/**
 * useViewTransition Hook
 * 
 * Provides smooth page transitions using the View Transitions API.
 * Falls back to normal navigation when API is not supported.
 * 
 * @see https://developer.chrome.com/docs/web-platform/view-transitions
 */

import { useCallback, useTransition } from 'react';
import { useRouter } from 'next/navigation';

export function useViewTransition() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const navigate = useCallback((href: string) => {
    // Check if View Transitions API is supported
    if (!document.startViewTransition) {
      router.push(href);
      return;
    }

    // Use View Transitions API for smooth animation
    document.startViewTransition(() => {
      startTransition(() => {
        router.push(href);
      });
    });
  }, [router, startTransition]);

  const replace = useCallback((href: string) => {
    if (!document.startViewTransition) {
      router.replace(href);
      return;
    }

    document.startViewTransition(() => {
      startTransition(() => {
        router.replace(href);
      });
    });
  }, [router, startTransition]);

  return { navigate, replace, isPending };
}
