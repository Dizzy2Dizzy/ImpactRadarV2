'use client';

import * as Sentry from '@sentry/nextjs';
import { Button } from '@/components/ui/button';

export default function SentryTestPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-bold">Sentry Test Page</h1>
      <p className="text-muted-foreground mb-4">
        Click buttons below to test Sentry error monitoring
      </p>
      
      <div className="flex flex-col gap-3">
        <Button
          onClick={() => {
            throw new Error('Sentry Frontend Test: Uncaught Error');
          }}
          variant="destructive"
        >
          Test Uncaught Error
        </Button>

        <Button
          onClick={() => {
            try {
              throw new Error('Sentry Frontend Test: Caught Error');
            } catch (error) {
              Sentry.captureException(error);
            }
          }}
          variant="outline"
        >
          Test Caught Error
        </Button>

        <Button
          onClick={() => {
            Sentry.captureMessage('Sentry Frontend Test: Info Message', 'info');
          }}
        >
          Test Info Message
        </Button>
      </div>
    </div>
  );
}
