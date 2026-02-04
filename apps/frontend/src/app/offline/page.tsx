'use client';

import { WifiOff, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="text-center max-w-md">
        <div className="mb-6 p-4 bg-muted rounded-full inline-block">
          <WifiOff className="h-12 w-12 text-muted-foreground" />
        </div>
        
        <h1 className="text-2xl font-bold mb-2">You&apos;re Offline</h1>
        
        <p className="text-muted-foreground mb-6">
          It looks like you&apos;ve lost your internet connection. 
          Some features may be unavailable until you reconnect.
        </p>
        
        <div className="space-y-3">
          <Button
            onClick={() => window.location.reload()}
            className="w-full"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
          
          <p className="text-xs text-muted-foreground">
            Your work is saved locally and will sync when you&apos;re back online.
          </p>
        </div>
      </div>
    </div>
  );
}
