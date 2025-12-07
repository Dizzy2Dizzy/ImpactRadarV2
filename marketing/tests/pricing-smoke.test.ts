/**
 * Pricing Page Smoke Test
 * Verifies all required plan strings and features are present
 */

import { plans, comparisonFeatures } from '../data/plans';

const requiredStrings = {
  free: [
    'View all public events',
    'Basic filtering & search',
    'Watchlist (up to 3 tickers)',
    'Delayed alerts (15-minute delay)',
    'Read-only dashboard access',
  ],
  pro: [
    'Everything in Free',
    'Real-time event feed (no delay)',
    'Unlimited watchlists',
    'Email & SMS alerts',
    'Impact score + confidence filters',
    'CSV/JSON export',
    'API access (10k calls/mo) — Research tier',
    'Priority computation lane',
    'Email support',
  ],
  team: [
    'Everything in Pro',
    'Up to 10 seats + team management',
    'SSO (Google/OIDC)',
    'Dedicated computation lane',
    'API access (100k calls/mo)',
    'Slack/Discord/Webhook alerts',
    'Dedicated support + SLA',
  ],
};

function runSmokeTest() {
  console.log('Running Pricing Page Smoke Test...\n');

  let passed = true;

  // Test 1: Verify plan count
  if (plans.length !== 3) {
    console.error(`❌ Expected 3 plans, found ${plans.length}`);
    passed = false;
  } else {
    console.log('✓ Plan count: 3');
  }

  // Test 2: Verify plan IDs
  const planIds = plans.map(p => p.id);
  if (!planIds.includes('free') || !planIds.includes('pro') || !planIds.includes('team')) {
    console.error(`❌ Missing plan IDs. Found: ${planIds.join(', ')}`);
    passed = false;
  } else {
    console.log('✓ Plan IDs: free, pro, team');
  }

  // Test 3: Verify pricing
  const freePlan = plans.find(p => p.id === 'free');
  const proPlan = plans.find(p => p.id === 'pro');
  const teamPlan = plans.find(p => p.id === 'team');

  if (freePlan?.price !== '$0') {
    console.error(`❌ Free plan price should be $0, found ${freePlan?.price}`);
    passed = false;
  } else {
    console.log('✓ Free plan: $0');
  }

  if (proPlan?.price !== '$49') {
    console.error(`❌ Pro plan price should be $49, found ${proPlan?.price}`);
    passed = false;
  } else {
    console.log('✓ Pro plan: $49');
  }

  if (teamPlan?.price !== '$199') {
    console.error(`❌ Team plan price should be $199, found ${teamPlan?.price}`);
    passed = false;
  } else {
    console.log('✓ Team plan: $199');
  }

  // Test 4: Verify CTAs
  if (freePlan?.cta !== 'Get Started') {
    console.error(`❌ Free CTA should be "Get Started", found "${freePlan?.cta}"`);
    passed = false;
  } else {
    console.log('✓ Free CTA: Get Started');
  }

  if (proPlan?.cta !== 'Start 7-day Free Trial') {
    console.error(`❌ Pro CTA should be "Start 7-day Free Trial", found "${proPlan?.cta}"`);
    passed = false;
  } else {
    console.log('✓ Pro CTA: Start 7-day Free Trial');
  }

  if (teamPlan?.cta !== 'Contact Sales') {
    console.error(`❌ Team CTA should be "Contact Sales", found "${teamPlan?.cta}"`);
    passed = false;
  } else {
    console.log('✓ Team CTA: Contact Sales');
  }

  // Test 5: Verify routing
  if (freePlan?.href !== '/signup?plan=free') {
    console.error(`❌ Free href should be "/signup?plan=free", found "${freePlan?.href}"`);
    passed = false;
  } else {
    console.log('✓ Free route: /signup?plan=free');
  }

  if (proPlan?.href !== '/signup?plan=pro&trial=7') {
    console.error(`❌ Pro href should be "/signup?plan=pro&trial=7", found "${proPlan?.href}"`);
    passed = false;
  } else {
    console.log('✓ Pro route: /signup?plan=pro&trial=7');
  }

  if (teamPlan?.href !== '/contact?topic=team') {
    console.error(`❌ Team href should be "/contact?topic=team", found "${teamPlan?.href}"`);
    passed = false;
  } else {
    console.log('✓ Team route: /contact?topic=team');
  }

  // Test 6: Verify all required feature strings
  console.log('\n Verifying feature strings...');
  
  for (const [planId, features] of Object.entries(requiredStrings)) {
    const plan = plans.find(p => p.id === planId);
    if (!plan) {
      console.error(`❌ ${planId} plan not found`);
      passed = false;
      continue;
    }

    const planFeatures = plan.features.map(f => f.text);
    for (const requiredFeature of features) {
      if (!planFeatures.includes(requiredFeature)) {
        console.error(`❌ ${planId}: Missing feature "${requiredFeature}"`);
        passed = false;
      }
    }
  }
  console.log('✓ All required feature strings present');

  // Test 7: Verify comparison table
  if (comparisonFeatures.length < 10) {
    console.error(`❌ Comparison table should have at least 10 features, found ${comparisonFeatures.length}`);
    passed = false;
  } else {
    console.log(`✓ Comparison table: ${comparisonFeatures.length} features`);
  }

  // Test 8: Verify tooltips
  const tooltipFeatures = [
    'Real-time event feed (no delay)',
    'API access (10k calls/mo) — Research tier',
    'Priority computation lane',
  ];

  for (const tooltipFeature of tooltipFeatures) {
    const hasTooltip = plans.some(plan =>
      plan.features.some(f => f.text === tooltipFeature && f.tooltip)
    );
    if (!hasTooltip) {
      console.error(`❌ Missing tooltip for "${tooltipFeature}"`);
      passed = false;
    }
  }
  console.log('✓ Required tooltips present');

  // Test 9: Verify badge
  if (proPlan?.badge !== 'Most Popular') {
    console.error(`❌ Pro badge should be "Most Popular", found "${proPlan?.badge}"`);
    passed = false;
  } else {
    console.log('✓ Pro badge: Most Popular');
  }

  // Test 10: Verify note
  if (proPlan?.note !== 'Billed monthly. Cancel anytime.') {
    console.error(`❌ Pro note should be "Billed monthly. Cancel anytime.", found "${proPlan?.note}"`);
    passed = false;
  } else {
    console.log('✓ Pro note: Billed monthly. Cancel anytime.');
  }

  console.log('\n' + '='.repeat(50));
  if (passed) {
    console.log('✅ All pricing smoke tests PASSED');
    process.exit(0);
  } else {
    console.log('❌ Some pricing smoke tests FAILED');
    process.exit(1);
  }
}

runSmokeTest();
