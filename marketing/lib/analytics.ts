// Performance monitoring and analytics tracking utilities

export type AnalyticsEvent = {
  name: string;
  properties?: Record<string, any>;
  timestamp?: number;
};

export type WebVitalsMetric = {
  name: 'CLS' | 'FCP' | 'FID' | 'LCP' | 'TTFB' | 'INP';
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  id: string;
};

class Analytics {
  private static instance: Analytics;
  private queue: AnalyticsEvent[] = [];
  private flushInterval: NodeJS.Timeout | null = null;

  private constructor() {
    if (typeof window !== 'undefined') {
      this.startAutoFlush();
    }
  }

  static getInstance(): Analytics {
    if (!Analytics.instance) {
      Analytics.instance = new Analytics();
    }
    return Analytics.instance;
  }

  /**
   * Track a custom event
   */
  track(eventName: string, properties?: Record<string, any>) {
    const event: AnalyticsEvent = {
      name: eventName,
      properties: {
        ...properties,
        url: typeof window !== 'undefined' ? window.location.href : undefined,
        userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      },
      timestamp: Date.now(),
    };

    this.queue.push(event);

    // Send to Plausible if available
    if (typeof window !== 'undefined' && (window as any).plausible) {
      (window as any).plausible(eventName, { props: properties });
    }

    // Flush if queue is large
    if (this.queue.length >= 10) {
      this.flush();
    }
  }

  /**
   * Track web vitals metrics
   */
  trackWebVitals(metric: WebVitalsMetric) {
    this.track('Web Vitals', {
      metric_name: metric.name,
      value: metric.value,
      rating: metric.rating,
      delta: metric.delta,
      metric_id: metric.id,
    });
  }

  /**
   * Track page view
   */
  trackPageView(page?: string) {
    const pagePath = page || (typeof window !== 'undefined' ? window.location.pathname : '/');
    this.track('Page View', { page: pagePath });
  }

  /**
   * Track conversion events
   */
  trackConversion(conversionType: string, value?: number, metadata?: Record<string, any>) {
    this.track('Conversion', {
      conversion_type: conversionType,
      value,
      ...metadata,
    });
  }

  /**
   * Track signup funnel steps
   */
  trackSignupStep(step: 'started' | 'email_entered' | 'plan_selected' | 'completed', plan?: string) {
    this.track('Signup Funnel', { step, plan });
  }

  /**
   * Track feature usage
   */
  trackFeatureUsage(feature: string, action: string, metadata?: Record<string, any>) {
    this.track('Feature Usage', {
      feature,
      action,
      ...metadata,
    });
  }

  /**
   * Track errors
   */
  trackError(error: Error, context?: Record<string, any>) {
    this.track('Error', {
      error_message: error.message,
      error_stack: error.stack,
      ...context,
    });
  }

  /**
   * Track API performance
   */
  trackApiCall(endpoint: string, duration: number, status: number) {
    this.track('API Call', {
      endpoint,
      duration_ms: duration,
      status_code: status,
    });
  }

  /**
   * Flush queued events
   */
  private async flush() {
    if (this.queue.length === 0) return;

    const events = [...this.queue];
    this.queue = [];

    try {
      // Send to backend analytics endpoint
      await fetch('/api/analytics/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events }),
      });
    } catch (error) {
      console.error('Failed to send analytics events:', error);
      // Re-queue failed events
      this.queue.push(...events);
    }
  }

  /**
   * Start auto-flush interval
   */
  private startAutoFlush() {
    this.flushInterval = setInterval(() => {
      this.flush();
    }, 30000); // Flush every 30 seconds

    // Flush on page unload
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.flush();
      });
    }
  }

  /**
   * Stop auto-flush
   */
  destroy() {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
      this.flushInterval = null;
    }
    this.flush();
  }
}

// Export singleton instance
export const analytics = Analytics.getInstance();

// Convenience functions
export const trackEvent = (name: string, properties?: Record<string, any>) => {
  analytics.track(name, properties);
};

export const trackPageView = (page?: string) => {
  analytics.trackPageView(page);
};

export const trackConversion = (type: string, value?: number, metadata?: Record<string, any>) => {
  analytics.trackConversion(type, value, metadata);
};

export const trackSignupStep = (step: 'started' | 'email_entered' | 'plan_selected' | 'completed', plan?: string) => {
  analytics.trackSignupStep(step, plan);
};

export const trackFeatureUsage = (feature: string, action: string, metadata?: Record<string, any>) => {
  analytics.trackFeatureUsage(feature, action, metadata);
};
