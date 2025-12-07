// Sentry error tracking configuration
// Note: Add SENTRY_DSN to environment secrets for production

export interface SentryConfig {
  dsn?: string;
  environment: string;
  tracesSampleRate: number;
  replaysSessionSampleRate: number;
  replaysOnErrorSampleRate: number;
}

export const sentryConfig: SentryConfig = {
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NODE_ENV || 'development',
  tracesSampleRate: 0.1, // 10% of transactions
  replaysSessionSampleRate: 0.1, // 10% of sessions
  replaysOnErrorSampleRate: 1.0, // 100% of sessions with errors
};

export function initSentry() {
  // Sentry will be initialized when DSN is provided
  // For now, we'll use a fallback error logger
  if (typeof window !== 'undefined' && !sentryConfig.dsn) {
    console.info('[Sentry] DSN not configured - using fallback error logging');
  }
}

export function captureException(error: Error, context?: Record<string, any>) {
  // If Sentry is available, use it
  if (typeof window !== 'undefined' && (window as any).Sentry) {
    (window as any).Sentry.captureException(error, { extra: context });
    return;
  }

  // Fallback: log to console and analytics
  console.error('[Error]', error, context);
  
  // Send to our analytics endpoint
  if (typeof window !== 'undefined') {
    fetch('/api/errors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: error.message,
        stack: error.stack,
        context,
        timestamp: Date.now(),
        url: window.location.href,
        userAgent: navigator.userAgent,
      }),
    }).catch(console.error);
  }
}

export function captureMessage(message: string, level: 'info' | 'warning' | 'error' = 'info', context?: Record<string, any>) {
  // If Sentry is available, use it
  if (typeof window !== 'undefined' && (window as any).Sentry) {
    (window as any).Sentry.captureMessage(message, { level, extra: context });
    return;
  }

  // Fallback: log to console
  const logFn = level === 'error' ? console.error : level === 'warning' ? console.warn : console.info;
  logFn('[Sentry]', message, context);
}

export function setUser(user: { id: string; email?: string; username?: string }) {
  if (typeof window !== 'undefined' && (window as any).Sentry) {
    (window as any).Sentry.setUser(user);
  }
}

export function clearUser() {
  if (typeof window !== 'undefined' && (window as any).Sentry) {
    (window as any).Sentry.setUser(null);
  }
}
