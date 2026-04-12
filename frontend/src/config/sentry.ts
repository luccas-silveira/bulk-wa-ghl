import * as Sentry from '@sentry/react';

export function initSentry(): void {
  const dsn = (import.meta.env as Record<string, string>).VITE_SENTRY_DSN;
  if (!dsn) return;
  Sentry.init({
    dsn,
    environment: import.meta.env.MODE,
    tracesSampleRate: 0.1,
  });
}

export { Sentry };
