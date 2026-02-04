'use client';

import { useEffect } from 'react';
import { onLCP, type LCPMetric } from 'web-vitals';

interface LCPData {
  url: string;
  selector: string;
  value: number;
}

/**
 * Hook to report LCP data for optimization insights
 * Use this to identify which elements are your LCP candidates
 */
export function useLCPReporter() {
  useEffect(() => {
    onLCP((metric: LCPMetric) => {
      const attribution = (metric as unknown as { attribution?: { element?: string } }).attribution;

      if (attribution?.element) {
        const data: LCPData = {
          url: window.location.pathname,
          selector: attribution.element,
          value: metric.value,
        };

        // Send to analytics endpoint
        if (navigator.sendBeacon) {
          navigator.sendBeacon('/api/v2/metrics/lcp', JSON.stringify(data));
        }

        // Log in development
        if (process.env.NODE_ENV === 'development') {
          console.log('[LCP]', data);
        }
      }
    });
  }, []);
}
