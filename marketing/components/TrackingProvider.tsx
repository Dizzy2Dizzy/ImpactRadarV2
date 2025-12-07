"use client";

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { analytics } from '@/lib/analytics';

export function TrackingProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Track page views on route changes
    if (pathname) {
      analytics.trackPageView(pathname);
      
      // Track special page views
      if (pathname === '/pricing') {
        analytics.track('Pricing Page View', {
          source: searchParams?.get('source'),
        });
      }
      
      if (pathname === '/signup') {
        const plan = searchParams?.get('plan');
        analytics.trackSignupStep('started', plan || undefined);
      }
      
      if (pathname === '/blog') {
        analytics.track('Blog Visit');
      }
      
      if (pathname === '/affiliate') {
        analytics.track('Affiliate Program View');
      }
    }
  }, [pathname, searchParams]);

  // Track exit intent
  useEffect(() => {
    const handleMouseLeave = (e: MouseEvent) => {
      if (e.clientY <= 0) {
        analytics.track('Exit Intent', {
          page: pathname,
        });
      }
    };

    document.addEventListener('mouseleave', handleMouseLeave);
    return () => document.removeEventListener('mouseleave', handleMouseLeave);
  }, [pathname]);

  return <>{children}</>;
}
