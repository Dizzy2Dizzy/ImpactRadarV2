'use client';

import { Tooltip } from '@/components/ui/tooltip';

interface InfoTierBadgeProps {
  tier: string;
  subtype?: string | null;
}

export function InfoTierBadge({ tier, subtype }: InfoTierBadgeProps) {
  const isPrimary = tier === 'primary';
  
  const tooltipText = isPrimary
    ? 'Primary: Direct corporate/financial events linked to price moves (SEC filings, FDA approvals, earnings, etc.)'
    : 'Secondary: Contextual risk factors (environmental, infrastructure, geopolitical)';
  
  return (
    <Tooltip content={tooltipText}>
      <span
        className={`
          inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
          ${isPrimary 
            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' 
            : 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
          }
        `}
      >
        {isPrimary ? 'Primary' : 'Secondary'}
        {subtype && (
          <span className="ml-1 opacity-75">
            · {formatSubtype(subtype)}
          </span>
        )}
      </span>
    </Tooltip>
  );
}

function formatSubtype(subtype: string): string {
  const subtypeLabels: Record<string, string> = {
    'ipo': 'IPO',
    'earnings': 'Earnings',
    'ma': 'M&A',
    'regulatory_primary': 'Regulatory',
    'ownership_change': 'Ownership',
    'proxy': 'Proxy',
    'material_event': 'Material Event',
    'financing': 'Financing',
    'product': 'Product',
    'legal': 'Legal',
    'announcement': 'Announcement',
    'executive_change': 'Executive'
  };
  
  return subtypeLabels[subtype] || subtype;
}
