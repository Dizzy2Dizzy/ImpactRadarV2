import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  
  tracesSampleRate: 0.1,
  
  debug: false,
  
  replaysOnErrorSampleRate: 1.0,
  
  replaysSessionSampleRate: 0.01,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  beforeSend(event) {
    if (event.user) {
      delete event.user.email;
      delete event.user.ip_address;
    }

    if (event.request?.cookies) {
      event.request.cookies = {};
    }

    if (event.request?.headers) {
      const headers = event.request.headers;
      if (headers['authorization']) headers['authorization'] = 'REDACTED';
      if (headers['cookie']) headers['cookie'] = 'REDACTED';
    }

    return event;
  },
});
