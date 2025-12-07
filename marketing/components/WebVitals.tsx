"use client";

import { useEffect } from 'react';
import { useReportWebVitals } from 'next/web-vitals';
import { analytics } from '@/lib/analytics';

export function WebVitals() {
  useReportWebVitals((metric) => {
    // Map Next.js metric to our analytics format
    const webVitalsMetric = {
      name: metric.name as 'CLS' | 'FCP' | 'FID' | 'LCP' | 'TTFB' | 'INP',
      value: metric.value,
      rating: metric.rating as 'good' | 'needs-improvement' | 'poor',
      delta: metric.delta,
      id: metric.id,
    };

    analytics.trackWebVitals(webVitalsMetric);
  });

  return null;
}
