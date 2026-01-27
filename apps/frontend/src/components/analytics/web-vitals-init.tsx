'use client';

import { useEffect } from 'react';
import { initWebVitals } from '@/lib/analytics/web-vitals';

export function WebVitalsInit() {
  useEffect(() => {
    initWebVitals();
  }, []);
  
  return null;
}
