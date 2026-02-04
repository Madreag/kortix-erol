'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

// Check if user recently dismissed the prompt (before component renders)
function wasRecentlyDismissed(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    const dismissed = localStorage.getItem('pwa-prompt-dismissed');
    if (dismissed) {
      const dismissedTime = parseInt(dismissed);
      const sevenDays = 7 * 24 * 60 * 60 * 1000;
      return Date.now() - dismissedTime < sevenDays;
    }
  } catch {
    // localStorage not available
  }
  return false;
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);

  // Check dismissal state on mount (before any visibility logic)
  useEffect(() => {
    if (wasRecentlyDismissed()) {
      setIsDismissed(true);
    }
  }, []);

  useEffect(() => {
    // Don't set up listeners if already dismissed
    if (isDismissed) return;
    
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
      return;
    }

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      
      // Show prompt after delay (don't interrupt initial experience)
      // Only show if not dismissed
      setTimeout(() => {
        if (!wasRecentlyDismissed()) {
          setIsVisible(true);
        }
      }, 30000); // 30 seconds
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setIsVisible(false);
      setDeferredPrompt(null);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, [isDismissed]);

  const handleInstall = async () => {
    if (!deferredPrompt) return;

    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      setIsVisible(false);
    }
    
    setDeferredPrompt(null);
  };

  const handleDismiss = () => {
    setIsVisible(false);
    setIsDismissed(true);
    // Don't show again for 7 days
    try {
      localStorage.setItem('pwa-prompt-dismissed', Date.now().toString());
    } catch {
      // localStorage not available
    }
  };

  if (!isVisible || isInstalled || isDismissed || !deferredPrompt) return null;

  return (
    <div
      className={cn(
        'fixed bottom-20 left-4 right-4 md:left-auto md:right-4 md:w-80',
        'bg-card border rounded-lg shadow-xl p-4 z-50',
        'animate-in slide-in-from-bottom-5 duration-300'
      )}
    >
      <button
        onClick={handleDismiss}
        className="absolute top-2 right-2 p-1 hover:bg-muted rounded"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
      
      <div className="flex items-start gap-3">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Download className="h-6 w-6 text-primary" />
        </div>
        
        <div className="flex-1">
          <h3 className="font-semibold text-sm">Install Kortix</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Add to your home screen for faster access and offline support.
          </p>
          
          <Button
            onClick={handleInstall}
            size="sm"
            className="mt-3 w-full"
          >
            Install App
          </Button>
        </div>
      </div>
    </div>
  );
}
