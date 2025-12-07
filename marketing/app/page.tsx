import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Hero from "@/components/Hero";
import { Section } from "@/components/Section";
import { FeaturedEventsSection } from "@/components/FeaturedEventsSection";
import { ScannerStatus } from "@/components/ScannerStatus";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Shield, Lock, CheckCircle2, TrendingUp, Target, PieChart, Brain, History, Bell, FileDown } from "lucide-react";

async function fetchFeaturedEvents() {
  try {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8080';
    const url = `${backendUrl}/events/featured`;
    
    const response = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
      signal: AbortSignal.timeout(5000),
    });
    
    if (!response.ok) {
      console.error('Failed to fetch featured events:', response.status);
      return [];
    }
    
    const events = await response.json();
    
    if (!Array.isArray(events) || events.length === 0) {
      return [];
    }
    
    return events.map((event: any) => {
      const directionMap: Record<string, 'positive' | 'negative' | 'neutral'> = {
        'bullish': 'positive',
        'bearish': 'negative',
        'neutral': 'neutral',
      };
      
      const eventDate = new Date(event.date);
      const formattedDate = eventDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric',
        timeZone: 'America/New_York'
      });
      
      return {
        id: event.id,
        title: event.title,
        company: event.ticker,
        date: formattedDate,
        rawDate: event.date,
        category: event.event_type,
        score: event.impact_score,
        direction: directionMap[event.direction] || 'neutral',
        sourceUrl: event.source_url,
      };
    });
  } catch (error) {
    console.error('Error fetching featured events:', error);
    return [];
  }
}

const scanners = [
  {
    name: "SEC EDGAR",
    lastRun: "2 min ago",
    discoveries: 12,
    status: "success" as const,
  },
  {
    name: "FDA Announcements",
    lastRun: "5 min ago",
    discoveries: 3,
    status: "success" as const,
  },
  {
    name: "Company Releases",
    lastRun: "8 min ago",
    discoveries: 7,
    status: "success" as const,
  },
];

const advancedFeatures = [
  {
    icon: <Target className="h-6 w-6" />,
    title: "Trade Signals",
    description: "AI-generated entry/exit targets with stop-loss, take-profit, and R/R ratios",
    badge: "NEW",
  },
  {
    icon: <PieChart className="h-6 w-6" />,
    title: "Sector Analysis",
    description: "Rotation signals and momentum scoring to identify market trends",
    badge: "NEW",
  },
  {
    icon: <Brain className="h-6 w-6" />,
    title: "Model Explainability",
    description: "SHAP-based visualizations showing why predictions are made",
    badge: "NEW",
  },
  {
    icon: <History className="h-6 w-6" />,
    title: "Pattern Matching",
    description: "Find similar historical events and their outcomes",
    badge: "NEW",
  },
  {
    icon: <Bell className="h-6 w-6" />,
    title: "Custom Alerts",
    description: "User-defined thresholds with flexible conditions",
    badge: "NEW",
  },
  {
    icon: <FileDown className="h-6 w-6" />,
    title: "Data Export",
    description: "CSV export for events and portfolio analysis",
    badge: "NEW",
  },
];

export default async function HomePage() {
  const featuredEvents = await fetchFeaturedEvents();
  
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <Hero />

        <Section>
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-4">
              Track <span className="text-[--primary]">1000+ events</span> across
              1500+ companies
            </h2>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto">
              Filter by sector, company, and category. Never miss a
              market-moving announcement.
            </p>
          </div>
          <FeaturedEventsSection events={featuredEvents} />
        </Section>

        <Section className="bg-[--panel]/50">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-6">
                Deterministic{" "}
                <span className="text-[--accent]">impact scoring</span>
              </h2>
              <p className="text-lg text-[--muted] mb-8">
                Every event receives a 0-100 impact score with direction,
                confidence, and detailed rationale. No black boxes.
              </p>
              <ul className="space-y-4">
                {[
                  "FDA events: 70-95 impact with 85%+ confidence",
                  "SEC 8-K filings: 65 impact, sector-adjusted",
                  "Earnings reports: 60-80 with beat/miss analysis",
                  "Product launches: 50-65 with market context",
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative rounded-3xl border border-white/10 bg-[--bg] p-8">
              <div className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                  <div>
                    <div className="text-sm text-[--muted]">FDA Approval</div>
                    <div className="text-lg font-semibold text-[--text]">
                      +92 Impact
                    </div>
                  </div>
                  <TrendingUp className="h-8 w-8 text-green-400" />
                </div>
                <div className="text-sm text-[--muted] leading-relaxed">
                  <span className="font-medium text-[--text]">Rationale:</span>{" "}
                  FDA approval typically triggers 20-40% upside in biotech
                  stocks, with high confidence based on historical data.
                </div>
              </div>
            </div>
          </div>
        </Section>

        <Section>
          <div className="text-center mb-12">
            <span className="inline-block px-4 py-1.5 text-sm font-semibold bg-green-500/20 text-green-400 rounded-full mb-4">
              November 2025 Release
            </span>
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-4">
              Advanced <span className="text-[--primary]">analytics</span> suite
            </h2>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto">
              New quantitative tools for professional traders: trade signals, sector analysis, 
              AI explainability, and more.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {advancedFeatures.map((feature, i) => (
              <div
                key={i}
                className="rounded-2xl border border-white/10 bg-[--panel] p-6 hover:border-[--primary]/30 transition-colors"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-[--primary]/10 text-[--primary]">
                    {feature.icon}
                  </div>
                  {feature.badge && (
                    <span className="px-2 py-0.5 text-xs font-bold bg-green-500/20 text-green-400 rounded-full">
                      {feature.badge}
                    </span>
                  )}
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-[--muted]">{feature.description}</p>
              </div>
            ))}
          </div>
          <div className="mt-8 text-center">
            <Button variant="outline" size="lg" asChild>
              <Link href="/product">View All Features</Link>
            </Button>
          </div>
        </Section>

        <Section className="bg-[--panel]/50">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-6">
                Trade signals with{" "}
                <span className="text-[--accent]">precision</span>
              </h2>
              <p className="text-lg text-[--muted] mb-8">
                Get AI-generated trade recommendations based on event analysis. 
                Every signal includes entry price, stop-loss, take-profit, and position sizing.
              </p>
              <ul className="space-y-4">
                {[
                  "Entry targets based on real-time market data",
                  "Stop-loss at 5% or 2x ATR for risk management",
                  "Take-profit scaled to event impact score",
                  "Position sizing from 1-5% based on confidence",
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative rounded-3xl border border-white/10 bg-[--bg] p-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3 mb-4">
                  <TrendingUp className="h-5 w-5 text-green-400" />
                  <span className="text-lg font-bold text-[--text]">AAPL</span>
                  <span className="px-2 py-0.5 text-xs font-semibold bg-green-500/20 text-green-400 rounded">
                    ENTRY
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[--muted] block">Entry</span>
                    <span className="font-medium text-[--text]">$271.14</span>
                  </div>
                  <div>
                    <span className="text-[--muted] block">Stop Loss</span>
                    <span className="font-medium text-red-400">$257.58</span>
                  </div>
                  <div>
                    <span className="text-[--muted] block">Take Profit</span>
                    <span className="font-medium text-green-400">$295.54</span>
                  </div>
                  <div>
                    <span className="text-[--muted] block">R/R Ratio</span>
                    <span className="font-bold text-yellow-400">1.8:1</span>
                  </div>
                </div>
                <div className="pt-4 border-t border-white/10">
                  <span className="text-xs text-[--muted]">
                    Based on SEC 8-K event with 60 impact score. Position Size: 2.6%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </Section>

        <Section id="demo">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-4">
              Multi-source{" "}
              <span className="text-[--primary]">ingestion</span>
            </h2>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto">
              Automated scanners monitor SEC, FDA, and company announcements
              24/7 with real-time updates.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {scanners.map((scanner, i) => (
              <ScannerStatus key={i} {...scanner} />
            ))}
          </div>
        </Section>

        <Section className="bg-[--panel]/50">
          <div className="text-center max-w-6xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-6">
              Portfolio impact{" "}
              <span className="text-[--accent]">before it happens</span>
            </h2>
            <p className="text-lg text-[--muted] mb-12">
              See potential P&L impact on your positions before earnings and
              events land. Stay ahead of the market.
            </p>
            <div className="rounded-3xl border border-white/10 bg-[--bg] p-12 md:p-16">
              <div className="text-base md:text-lg text-[--muted] text-center mb-6">
                Portfolio Earnings Tracker
              </div>
              <div className="text-5xl md:text-6xl font-bold text-[--text] text-center mb-4">
                +$12,450
              </div>
              <div className="text-base md:text-lg text-green-400 text-center">
                Estimated impact from upcoming events
              </div>
            </div>
          </div>
        </Section>

        <Section>
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-4">
              Enterprise-grade{" "}
              <span className="text-[--primary]">security</span>
            </h2>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto">
              Bank-level encryption, 2-step verification, and complete data
              sovereignty.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {[
              {
                icon: <Shield className="h-6 w-6" />,
                title: "bcrypt + salt",
                description: "Industry-standard password hashing",
              },
              {
                icon: <Lock className="h-6 w-6" />,
                title: "Email & SMS verify",
                description: "Two-factor authentication built-in",
              },
              {
                icon: <CheckCircle2 className="h-6 w-6" />,
                title: "Session security",
                description: "Encrypted sessions with auto-expiry",
              },
            ].map((item, i) => (
              <div
                key={i}
                className="rounded-2xl border border-white/10 bg-[--panel] p-6 text-center"
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                  {item.icon}
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-[--muted]">{item.description}</p>
              </div>
            ))}
          </div>
        </Section>

        <Section className="bg-gradient-to-b from-transparent to-[--panel]/50">
          <div className="rounded-3xl border border-white/10 bg-[--panel] p-12 text-center">
            <h2 className="text-3xl md:text-5xl font-semibold text-[--text] mb-6">
              Ready to stay ahead?
            </h2>
            <p className="text-lg text-[--muted] mb-8 max-w-2xl mx-auto">
              Join traders and funds using Impact Radar to track
              market-moving events in real-time.
            </p>
            <div className="flex gap-4 justify-center flex-wrap">
              <Button size="lg" asChild>
                <Link href="/signup">Start free trial</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href="/product">See all features</Link>
              </Button>
            </div>
          </div>
        </Section>
      </main>
      <Footer />
    </div>
  );
}
