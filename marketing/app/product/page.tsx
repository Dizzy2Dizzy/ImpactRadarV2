import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Section } from "@/components/Section";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  Database,
  Zap,
  BarChart3,
  Bell,
  Shield,
  Target,
  PieChart,
  Brain,
  History,
  Mail,
  FileDown,
  Palette,
  Sliders,
} from "lucide-react";
import Link from "next/link";

interface Feature {
  icon: React.ReactNode;
  name: string;
  description: string;
  details: string[];
  badge?: string;
  video?: string;
  image?: string;
}

const features: Feature[] = [
  {
    icon: <TrendingUp className="h-6 w-6" />,
    name: "Event Tracking",
    description:
      "Monitor 1000+ events across 1500+ companies with real-time updates. Filter by sector, event type, and impact score.",
    details: [
      "Earnings calls with beat/miss analysis",
      "FDA approvals, rejections, and AdCom meetings",
      "SEC 8-K, 10-K, and 10-Q filings",
      "Product launches and company announcements",
    ],
    image: "/features/event-tracking.jpg",
  },
  {
    icon: <Target className="h-6 w-6" />,
    name: "Trade Signals",
    description:
      "AI-generated trade recommendations with precise entry/exit targets, stop-loss levels, and position sizing based on event impact analysis.",
    badge: "NEW",
    details: [
      "Entry price targets based on current market data",
      "Stop-loss levels using ATR or fixed percentage",
      "Take-profit targets calculated from impact scores",
      "Risk/reward ratios and position sizing (1-5% of portfolio)",
    ],
    image: "/features/trade-signals.jpg",
  },
  {
    icon: <PieChart className="h-6 w-6" />,
    name: "Sector Analysis",
    description:
      "Track sector-level performance with rotation signals, momentum scoring, and capital flow analysis to identify market trends.",
    badge: "NEW",
    details: [
      "Real-time sector performance metrics",
      "Rotation signals for inflow/outflow detection",
      "Momentum scoring and trend identification",
      "Cross-sector correlation analysis",
    ],
    image: "/features/sector-analysis.jpg",
  },
  {
    icon: <Brain className="h-6 w-6" />,
    name: "Model Explainability",
    description:
      "Understand why predictions are made with SHAP-based feature contribution visualizations. Full transparency into the AI decision-making process.",
    badge: "NEW",
    details: [
      "SHAP value visualizations for each prediction",
      "Feature importance rankings",
      "Multi-horizon support (1d/7d/30d predictions)",
      "Transparent AI reasoning with no black boxes",
    ],
    image: "/features/explainability.jpg",
  },
  {
    icon: <Database className="h-6 w-6" />,
    name: "Multi-Source Scanners",
    description:
      "Automated ingestion from SEC EDGAR, FDA.gov, and company press releases with duplicate detection.",
    details: [
      "24/7 automated monitoring",
      "Rate-limited, respectful scraping",
      "Direct links to original sources",
      "Historical event archive",
    ],
    image: "/features/multi-source-scanners.jpg",
  },
  {
    icon: <History className="h-6 w-6" />,
    name: "Historical Pattern Matching",
    description:
      "Discover similar historical events and their outcomes. Pattern library with outcome tracking helps predict future price movements.",
    badge: "NEW",
    details: [
      "Pattern library of historical events",
      "Similar event lookup by type and sector",
      "Outcome tracking and success rates",
      "Learn from past market reactions",
    ],
    image: "/features/pattern-matching.jpg",
  },
  {
    icon: <Zap className="h-6 w-6" />,
    name: "Backtesting",
    description:
      "Validate prediction accuracy against actual stock price movements. Market Echo Engine learns from every event to improve future predictions.",
    details: [
      "Multi-horizon validation (1d, 5d, 20d price movements)",
      "ML-adjusted predictions with confidence scores",
      "Separate tracking for deterministic vs ML accuracy",
      "SPY-normalized abnormal return calculations",
    ],
    video: "/backtesting-demo.mov",
  },
  {
    icon: <Bell className="h-6 w-6" />,
    name: "Custom Alert Rules",
    description:
      "Define your own alert thresholds with flexible conditions. Get notified when events match your specific criteria.",
    badge: "NEW",
    details: [
      "User-defined threshold conditions (>, <, =)",
      "Filter by impact score, sector, or ticker",
      "Email and in-app notification delivery",
      "Digest mode for consolidated updates",
    ],
    image: "/features/custom-alerts.jpg",
  },
  {
    icon: <BarChart3 className="h-6 w-6" />,
    name: "Portfolio Tracking",
    description:
      "See potential P&L impact on your positions before events happen. Discover event correlations and patterns across your holdings.",
    details: [
      "CSV upload for portfolio holdings",
      "Position-level event exposure analysis",
      "Correlation engine finds event sequences and patterns",
      "Timeline visualization of related events",
    ],
    image: "/features/portfolio-tracking.jpg",
  },
  {
    icon: <Mail className="h-6 w-6" />,
    name: "Email Digests",
    description:
      "Subscribe to daily or weekly email summaries with configurable content sections. Stay informed without dashboard fatigue.",
    badge: "NEW",
    details: [
      "Daily and weekly digest options",
      "Configurable content sections",
      "Watchlist-focused event summaries",
      "Powered by Resend for reliable delivery",
    ],
    image: "/features/email-digests.jpg",
  },
  {
    icon: <FileDown className="h-6 w-6" />,
    name: "CSV Export",
    description:
      "Export event data and portfolio analysis in CSV format for offline analysis, reporting, or integration with your existing tools.",
    badge: "NEW",
    details: [
      "Event data export with all metadata",
      "Portfolio analysis reports",
      "Custom date range selection",
      "Compatible with Excel and data tools",
    ],
    image: "/features/csv-export.jpg",
  },
  {
    icon: <Shield className="h-6 w-6" />,
    name: "Market Echo Engine",
    description:
      "Self-learning ML system that continuously improves event impact predictions by analyzing realized stock price movements.",
    details: [
      "Hierarchical XGBoost models trained on 1d/5d/20d horizons",
      "Event-family-specific models with global fallback",
      "Automated daily training with 50+ engineered features",
      "Direction accuracy and prediction quality tracking",
    ],
    image: "/features/market-echo-engine.jpg",
  },
  {
    icon: <Sliders className="h-6 w-6" />,
    name: "Saved Filters & Preferences",
    description:
      "Save your favorite filter combinations and dashboard settings. Your preferences persist across sessions for a personalized experience.",
    badge: "NEW",
    details: [
      "Save custom filter combinations",
      "Persistent dashboard preferences",
      "Quick access to saved views",
      "Per-user settings storage",
    ],
    image: "/features/saved-filters.jpg",
  },
  {
    icon: <Palette className="h-6 w-6" />,
    name: "Dark/Light Mode",
    description:
      "Toggle between dark and light themes to match your preference. System-aware mode automatically adapts to your device settings.",
    badge: "NEW",
    details: [
      "Dark, light, and system-aware modes",
      "Instant theme switching",
      "Consistent styling across all pages",
      "Reduced eye strain in low-light environments",
    ],
    image: "/features/theme-toggle.jpg",
  },
];

export default function ProductPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Everything you need to{" "}
              <span className="text-[--primary]">track markets</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              A comprehensive platform for active traders and small funds
              tracking regulatory filings, FDA announcements, and company
              releases.
            </p>
            <div className="mt-10 flex items-center justify-center gap-x-6">
              <Button size="lg" asChild>
                <Link href="/app">Start Tracking</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/pricing">View Pricing</Link>
              </Button>
            </div>
          </div>

          <div className="mt-24 space-y-24">
            {features.map((feature, index) => (
              <Section key={feature.name}>
                <div
                  className={`grid lg:grid-cols-2 gap-12 items-center ${
                    index % 2 === 1 ? "lg:flex-row-reverse" : ""
                  }`}
                >
                  <div className={index % 2 === 1 ? "lg:order-2" : ""}>
                    <div className="flex items-center gap-3 mb-6">
                      <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                        {feature.icon}
                      </div>
                      {feature.badge && (
                        <span className="px-2.5 py-1 text-xs font-bold bg-green-500/20 text-green-400 rounded-full">
                          {feature.badge}
                        </span>
                      )}
                    </div>
                    <h2 className="text-3xl font-semibold text-[--text] mb-4">
                      {feature.name}
                    </h2>
                    <p className="text-lg text-[--muted] mb-6">
                      {feature.description}
                    </p>
                    <ul className="space-y-3">
                      {feature.details.map((detail) => (
                        <li
                          key={detail}
                          className="flex items-start gap-3 text-[--text]"
                        >
                          <span className="text-[--accent]">•</span>
                          <span>{detail}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className={index % 2 === 1 ? "lg:order-1" : ""}>
                    {feature.video ? (
                      <div className="rounded-3xl border border-white/10 bg-[--panel] overflow-hidden aspect-video">
                        <video
                          autoPlay
                          loop
                          muted
                          playsInline
                          className="w-full h-full object-cover"
                          style={{ objectPosition: '50% 60%' }}
                        >
                          <source src={feature.video} type="video/quicktime" />
                          <source src={feature.video} type="video/mp4" />
                          Your browser does not support the video tag.
                        </video>
                      </div>
                    ) : feature.image ? (
                      <div className="rounded-3xl border border-white/10 bg-[--panel] overflow-hidden aspect-video">
                        <img
                          src={feature.image}
                          alt={feature.name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="rounded-3xl border border-white/10 bg-[--panel] p-8 aspect-video flex items-center justify-center">
                        <div className="text-6xl opacity-20">
                          {feature.icon}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </Section>
            ))}
          </div>

          <Section className="bg-gradient-to-b from-transparent to-[--panel]/50">
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-12 text-center">
              <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-6">
                Ready to get started?
              </h2>
              <p className="text-lg text-[--muted] mb-8 max-w-2xl mx-auto">
                Join traders and funds using Impact Radar to stay ahead of
                market-moving events.
              </p>
              <Button size="lg" asChild>
                <Link href="/app">Start Free</Link>
              </Button>
            </div>
          </Section>
        </div>
      </main>
      <Footer />
    </div>
  );
}
