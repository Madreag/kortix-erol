import { onCLS, onINP, onLCP, onFCP, onTTFB } from 'web-vitals/attribution';

interface RUMMetric {
  name: string;
  value: number;
  rating: string;
  attribution?: unknown;
  metadata: {
    url: string;
    userAgent: string;
    connection?: string;
    region?: string;
    timestamp: number;
  };
}

class RUMReporter {
  private queue: RUMMetric[] = [];
  private flushTimeout: ReturnType<typeof setTimeout> | null = null;
  
  private readonly FLUSH_INTERVAL = 5000;
  private readonly MAX_QUEUE_SIZE = 20;
  
  init(): void {
    if (typeof window === 'undefined') return;
    
    const metadata = this.getMetadata();
    
    const report = (metric: { name: string; value: number; rating: string; attribution?: unknown }) => {
      this.queue.push({
        name: metric.name,
        value: metric.value,
        rating: metric.rating,
        attribution: metric.attribution,
        metadata,
      });
      
      if (this.queue.length >= this.MAX_QUEUE_SIZE) {
        this.flush();
      } else {
        this.scheduleFlush();
      }
    };
    
    onCLS(report);
    onINP(report);
    onLCP(report);
    onFCP(report);
    onTTFB(report);
  }
  
  private getMetadata() {
    return {
      url: window.location.href,
      userAgent: navigator.userAgent,
      connection: (navigator as { connection?: { effectiveType?: string } }).connection?.effectiveType,
      region: this.getCloudflareRegion(),
      timestamp: Date.now(),
    };
  }
  
  private getCloudflareRegion(): string | undefined {
    const cfRay = document.querySelector('meta[name="cf-ray"]')?.getAttribute('content');
    return cfRay?.split('-')[1];
  }
  
  private scheduleFlush(): void {
    if (this.flushTimeout) return;
    
    this.flushTimeout = setTimeout(() => {
      this.flush();
    }, this.FLUSH_INTERVAL);
  }
  
  private async flush(): Promise<void> {
    if (this.flushTimeout) {
      clearTimeout(this.flushTimeout);
      this.flushTimeout = null;
    }
    
    if (this.queue.length === 0) return;
    
    const metrics = [...this.queue];
    this.queue = [];
    
    const payload = JSON.stringify({ metrics });
    
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/rum', payload);
    } else {
      try {
        await fetch('/api/rum', {
          method: 'POST',
          body: payload,
          headers: { 'Content-Type': 'application/json' },
          keepalive: true,
        });
      } catch (error) {
        console.warn('Failed to send RUM metrics:', error);
      }
    }
  }
}

export const rumReporter = new RUMReporter();
