export type PlanId = 'free' | 'pro' | 'team';

export interface PlanFeature {
  text: string;
  tooltip?: string;
}

export interface Plan {
  id: PlanId;
  name: string;
  price: string;
  period: string;
  description: string;
  features: PlanFeature[];
  cta: string;
  href: string;
  highlighted: boolean;
  badge?: string;
  note?: string;
}

export const plans: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Track public events and browse the dashboard',
    features: [
      { text: 'View all public events' },
      { text: 'Basic filtering & search' },
      { text: 'Watchlist (up to 3 tickers)' },
      { text: 'Delayed alerts (15-minute delay)' },
      { text: 'Read-only dashboard access' },
    ],
    cta: 'Get Started',
    href: '/signup?plan=free',
    highlighted: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '$49',
    period: 'per month',
    description: 'Real-time signals and unlimited watchlists',
    features: [
      { text: 'Everything in Free' },
      { 
        text: 'Real-time event feed (no delay)',
        tooltip: 'Events delivered without delay while markets are open.'
      },
      { text: 'Unlimited watchlists' },
      { text: 'Email & SMS alerts' },
      { text: 'Impact score + confidence filters' },
      { text: 'CSV/JSON export' },
      { 
        text: 'API access (10k calls/mo) — Research tier',
        tooltip: 'Rate-limited requests per month across REST endpoints.'
      },
      { 
        text: 'Priority computation lane',
        tooltip: 'Your scans are scheduled ahead of free users to reduce time-to-signal.'
      },
      { text: 'Email support' },
    ],
    cta: 'Start 7-day Free Trial',
    href: '/signup?plan=pro&trial=7',
    highlighted: true,
    badge: 'Most Popular',
    note: 'Billed monthly. Cancel anytime.',
  },
  {
    id: 'team',
    name: 'Team',
    price: '$199',
    period: 'per month',
    description: 'Multi-seat access with SSO and priority processing',
    features: [
      { text: 'Everything in Pro' },
      { text: 'Up to 10 seats + team management' },
      { text: 'SSO (Google/OIDC)' },
      { 
        text: 'Dedicated computation lane',
        tooltip: 'Your scans are scheduled ahead of free users to reduce time-to-signal.'
      },
      { 
        text: 'API access (100k calls/mo)',
        tooltip: 'Rate-limited requests per month across REST endpoints.'
      },
      { text: 'Slack/Discord/Webhook alerts' },
      { text: 'Dedicated support + SLA' },
    ],
    cta: 'Contact Sales',
    href: '/contact?topic=team',
    highlighted: false,
  },
];

export interface ComparisonFeature {
  name: string;
  free: boolean | string;
  pro: boolean | string;
  team: boolean | string;
  tooltip?: string;
}

export const comparisonFeatures: ComparisonFeature[] = [
  {
    name: 'View all public events',
    free: true,
    pro: true,
    team: true,
  },
  {
    name: 'Basic filtering & search',
    free: true,
    pro: true,
    team: true,
  },
  {
    name: 'Watchlist (up to 3 tickers)',
    free: true,
    pro: 'Unlimited watchlists',
    team: 'Unlimited watchlists',
  },
  {
    name: 'Delayed alerts (15-minute delay)',
    free: true,
    pro: false,
    team: false,
  },
  {
    name: 'Read-only dashboard access',
    free: true,
    pro: true,
    team: true,
  },
  {
    name: 'Real-time event feed (no delay)',
    free: false,
    pro: true,
    team: true,
    tooltip: 'Events delivered without delay while markets are open.',
  },
  {
    name: 'Email & SMS alerts',
    free: false,
    pro: true,
    team: true,
  },
  {
    name: 'Impact score + confidence filters',
    free: false,
    pro: true,
    team: true,
  },
  {
    name: 'CSV/JSON export',
    free: false,
    pro: true,
    team: true,
  },
  {
    name: 'API access (10k calls/mo) — Research tier',
    free: false,
    pro: true,
    team: '100k calls/mo',
    tooltip: 'Rate-limited requests per month across REST endpoints.',
  },
  {
    name: 'Priority computation lane',
    free: false,
    pro: true,
    team: 'Dedicated computation lane',
    tooltip: 'Your scans are scheduled ahead of free users to reduce time-to-signal.',
  },
  {
    name: 'Email support',
    free: false,
    pro: true,
    team: true,
  },
  {
    name: 'Up to 10 seats + team management',
    free: false,
    pro: false,
    team: true,
  },
  {
    name: 'SSO (Google/OIDC)',
    free: false,
    pro: false,
    team: true,
  },
  {
    name: 'Slack/Discord/Webhook alerts',
    free: false,
    pro: false,
    team: true,
  },
  {
    name: 'Dedicated support + SLA',
    free: false,
    pro: false,
    team: true,
  },
];
