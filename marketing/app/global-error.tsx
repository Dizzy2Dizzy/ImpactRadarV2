'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html>
      <body className="min-h-screen flex flex-col items-center justify-center bg-background p-8">
        <div className="max-w-md text-center space-y-4">
          <h1 className="text-4xl font-bold text-destructive">Something went wrong</h1>
          <p className="text-muted-foreground">
            We've been notified and are looking into it. Please try again.
          </p>
          <div className="flex gap-3 justify-center">
            <Button onClick={() => reset()}>
              Try Again
            </Button>
            <Button variant="outline" onClick={() => window.location.href = '/'}>
              Go Home
            </Button>
          </div>
        </div>
      </body>
    </html>
  );
}
