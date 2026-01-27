import { onCLS, onINP, onLCP, onFCP, onTTFB } from 'web-vitals/attribution';

type MetricName = 'CLS' | 'INP' | 'LCP' | 'FCP' | 'TTFB';

interface VitalMetric {
  name: MetricName;
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  attribution?: unknown;
  path: string;
}

const THRESHOLDS: Record<MetricName, { good: number; poor: number }> = {
  LCP: { good: 2500, poor: 4000 },
  INP: { good: 200, poor: 500 },
  CLS: { good: 0.1, poor: 0.25 },
  FCP: { good: 1800, poor: 3000 },
  TTFB: { good: 800, poor: 1800 },
};

function getRating(name: MetricName, value: number): 'good' | 'needs-improvement' | 'poor' {
  const threshold = THRESHOLDS[name];
  if (value <= threshold.good) return 'good';
  if (value <= threshold.poor) return 'needs-improvement';
  return 'poor';
}

function sendToAnalytics(metric: VitalMetric) {
  // Log in development
  if (process.env.NODE_ENV === 'development') {
    const color = metric.rating === 'good' ? '\x1b[32m' : metric.rating === 'poor' ? '\x1b[31m' : '\x1b[33m';
    console.log(`${color}[WebVital] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})\x1b[0m`);
  }
  
  // Send to PostHog if available
  if (typeof window !== 'undefined' && (window as any).posthog) {
    (window as any).posthog.capture('web_vital', {
      metric_name: metric.name,
      metric_value: metric.value,
      metric_rating: metric.rating,
      page_path: metric.path,
    });
  }
}

export function initWebVitals() {
  const path = typeof window !== 'undefined' ? window.location.pathname : '';
  
  const reportMetric = (metric: any) => {
    sendToAnalytics({
      name: metric.name,
      value: metric.value,
      rating: getRating(metric.name, metric.value),
      attribution: metric.attribution,
      path,
    });
  };

  onCLS(reportMetric);
  onINP(reportMetric);
  onLCP(reportMetric);
  onFCP(reportMetric);
  onTTFB(reportMetric);
}
