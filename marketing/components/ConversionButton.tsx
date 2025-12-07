"use client";

import { ReactNode } from 'react';
import Link from 'next/link';
import { analytics } from '@/lib/analytics';

interface ConversionButtonProps {
  href: string;
  children: ReactNode;
  conversionType?: string;
  metadata?: Record<string, any>;
  className?: string;
}

export function ConversionButton({
  href,
  children,
  conversionType = 'button_click',
  metadata,
  className = '',
}: ConversionButtonProps) {
  const handleClick = () => {
    analytics.track('Conversion Button Click', {
      conversion_type: conversionType,
      destination: href,
      ...metadata,
    });
  };

  return (
    <Link href={href} className={className} onClick={handleClick}>
      {children}
    </Link>
  );
}
