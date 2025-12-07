"use client";

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { analytics } from '@/lib/analytics';

/**
 * Hook to automatically track page views on route changes
 */
export function usePageTracking() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (pathname) {
      analytics.trackPageView(pathname);
    }
  }, [pathname, searchParams]);
}

/**
 * Hook to track conversion events with convenient API
 */
export function useConversionTracking() {
  return {
    trackSignupStarted: (plan?: string) => {
      analytics.trackSignupStep('started', plan);
    },
    trackEmailEntered: (plan?: string) => {
      analytics.trackSignupStep('email_entered', plan);
    },
    trackPlanSelected: (plan: string) => {
      analytics.trackSignupStep('plan_selected', plan);
    },
    trackSignupCompleted: (plan: string) => {
      analytics.trackSignupStep('completed', plan);
      analytics.trackConversion('signup', undefined, { plan });
    },
    trackUpgrade: (fromPlan: string, toPlan: string, value?: number) => {
      analytics.trackConversion('upgrade', value, { from_plan: fromPlan, to_plan: toPlan });
    },
    trackTrialStarted: (plan: string) => {
      analytics.trackConversion('trial_started', undefined, { plan });
    },
  };
}

/**
 * Hook to track feature usage
 */
export function useFeatureTracking() {
  return {
    trackClick: (feature: string, element: string) => {
      analytics.trackFeatureUsage(feature, 'click', { element });
    },
    trackView: (feature: string) => {
      analytics.trackFeatureUsage(feature, 'view');
    },
    trackInteraction: (feature: string, interaction: string, metadata?: Record<string, any>) => {
      analytics.trackFeatureUsage(feature, interaction, metadata);
    },
  };
}
