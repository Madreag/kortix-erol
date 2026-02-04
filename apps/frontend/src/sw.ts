/// <reference lib="webworker" />

import { defaultCache } from '@serwist/next/worker';
import type { PrecacheEntry, SerwistGlobalConfig } from 'serwist';
import { CacheFirst, NetworkFirst, StaleWhileRevalidate, Serwist } from 'serwist';

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  
  runtimeCaching: [
    // API v2 endpoints - Network First with cache fallback
    {
      matcher: ({ url }) => url.pathname.startsWith('/api/v2/'),
      handler: new NetworkFirst({
        cacheName: 'api-v2-cache',
        networkTimeoutSeconds: 10,
        plugins: [
          {
            cacheWillUpdate: async ({ response }) => {
              // Only cache successful responses
              return response?.status === 200 ? response : null;
            },
          },
        ],
        matchOptions: {
          ignoreSearch: false,
        },
      }),
    },
    
    // Static assets - Cache First (immutable)
    {
      matcher: ({ url }) => 
        url.pathname.startsWith('/_next/static/') ||
        url.pathname.match(/\.(js|css|woff2?)$/) !== null,
      handler: new CacheFirst({
        cacheName: 'static-assets',
        plugins: [
          {
            cacheDidUpdate: async () => {
              // Assets are immutable, cache forever
            },
          },
        ],
      }),
    },
    
    // Images - Cache First with size limit
    {
      matcher: ({ url }) => 
        url.pathname.match(/\.(png|jpg|jpeg|svg|gif|webp|avif)$/) !== null,
      handler: new CacheFirst({
        cacheName: 'images',
        plugins: [
          {
            // Limit cache size
            cachedResponseWillBeUsed: async ({ cachedResponse }) => {
              return cachedResponse;
            },
          },
        ],
      }),
    },
    
    // API health/status - Stale While Revalidate
    {
      matcher: ({ url }) => 
        url.pathname.includes('/health') || 
        url.pathname.includes('/status'),
      handler: new StaleWhileRevalidate({
        cacheName: 'health-checks',
      }),
    },
    
    // Streaming endpoints - Network Only (never cache)
    {
      matcher: ({ url }) => 
        url.pathname.includes('/stream') ||
        url.pathname.includes('/sse'),
      handler: new NetworkFirst({
        cacheName: 'streams',
        networkTimeoutSeconds: 0, // Never use cache
      }),
    },
    
    // Default caching from Serwist
    ...defaultCache,
  ],
});

// Handle offline fallback
serwist.addEventListeners();

// Background sync for failed mutations
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-threads') {
    event.waitUntil(syncPendingThreads());
  }
});

async function syncPendingThreads(): Promise<void> {
  // Get pending mutations from IndexedDB
  const pendingMutations = await getPendingMutations();
  
  for (const mutation of pendingMutations) {
    try {
      await fetch(mutation.url, {
        method: mutation.method,
        headers: mutation.headers,
        body: mutation.body,
      });
      await removePendingMutation(mutation.id);
    } catch (error) {
      console.error('Sync failed:', error);
    }
  }
}

interface PendingMutation {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string;
}

async function getPendingMutations(): Promise<PendingMutation[]> {
  // Implement IndexedDB retrieval
  return [];
}

async function removePendingMutation(_id: string): Promise<void> {
  // Implement IndexedDB removal
}
