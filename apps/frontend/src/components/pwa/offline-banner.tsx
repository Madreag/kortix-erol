'use client';

import { useOfflineStatus } from '@/hooks/use-offline-status';
import { WifiOff, Wifi } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';

export function OfflineBanner() {
  const { isOffline, wasOffline, isOnline } = useOfflineStatus();
  const [showReconnected, setShowReconnected] = useState(false);

  useEffect(() => {
    if (wasOffline && isOnline) {
      setShowReconnected(true);
      const timer = setTimeout(() => setShowReconnected(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [wasOffline, isOnline]);

  if (!isOffline && !showReconnected) return null;

  return (
    <div
      className={cn(
        'fixed bottom-4 left-1/2 -translate-x-1/2 z-50',
        'flex items-center gap-2 px-4 py-2 rounded-full shadow-lg',
        'text-sm font-medium transition-all duration-300',
        isOffline
          ? 'bg-amber-500 text-amber-950'
          : 'bg-green-500 text-green-950'
      )}
    >
      {isOffline ? (
        <>
          <WifiOff className="h-4 w-4" />
          <span>You&apos;re offline - some features may be limited</span>
        </>
      ) : (
        <>
          <Wifi className="h-4 w-4" />
          <span>Back online!</span>
        </>
      )}
    </div>
  );
}
