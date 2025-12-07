import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";
import { 
  BookOpen, 
  Search, 
  Building2, 
  Star, 
  Calendar, 
  Filter,
  TrendingUp,
  GitCompare,
  Users,
  BarChart3,
  Brain,
  Zap,
  LineChart,
  Target,
  Twitter,
  Radio,
  Code,
  FileDown,
  Sliders,
  Bell,
  Activity,
  Settings,
  ChevronRight,
  CheckCircle2,
  Lightbulb,
  CreditCard,
  PieChart,
  History,
  Mail,
  Palette,
  Save,
  StopCircle,
  DollarSign
} from "lucide-react";

const PlanBadge = ({ plan }: { plan: "Pro" | "Enterprise" }) => (
  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 ml-2">
    {plan} Plan
  </span>
);

export default function GuidePage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          {/* Hero Section */}
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Impact Radar <span className="text-[--primary]">Guide</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Master every feature of Impact Radar to track market events, validate predictions, and analyze events to make informed decisions. From basic event monitoring to advanced AI-powered analytics.
            </p>
          </div>

          {/* Quick Start Section */}
          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400">
                  <Zap className="h-6 w-6" />
                </div>
                <h2 className="text-2xl font-semibold text-[--text]">
                  Quick Start: Get Running in 5 Minutes
                </h2>
              </div>
              <ol className="space-y-4">
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-sm font-bold">1</span>
                  <div>
                    <strong className="text-[--text]">Create Your Account</strong>
                    <p className="text-sm text-[--muted] mt-1">Sign up at /signup to unlock the dashboard and start tracking market events across SEC filings, FDA announcements, earnings, and more.</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-sm font-bold">2</span>
                  <div>
                    <strong className="text-[--text]">Add Companies to Your Watchlist</strong>
                    <p className="text-sm text-[--muted] mt-1">Navigate to the Watchlist tab and add tickers you care about (e.g., AAPL, TSLA, NVDA). Get personalized event feeds for your portfolio.</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-sm font-bold">3</span>
                  <div>
                    <strong className="text-[--text]">Explore Recent Events</strong>
                    <p className="text-sm text-[--muted] mt-1">Browse the Events tab to see impact scores (0-100), direction predictions (positive/negative/neutral), and confidence ratings for each event.</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-sm font-bold">4</span>
                  <div>
                    <strong className="text-[--text]">Set Up Alerts</strong>
                    <p className="text-sm text-[--muted] mt-1">Configure alerts in the Alerts tab to get notified via email or in-app when high-impact events occur for your watchlist tickers or sectors.</p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full bg-blue-500/20 text-blue-400 text-sm font-bold">5</span>
                  <div>
                    <strong className="text-[--text]">Monitor the Live Tape</strong>
                    <p className="text-sm text-[--muted] mt-1">Open the Live Tape to see real-time market events streaming as they happen. Filter by ticker, event type, or minimum score.</p>
                  </div>
                </li>
              </ol>
            </div>
          </div>

          {/* Table of Contents */}
          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Feature Reference
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Jump to any section to learn about specific features:
              </p>
              <nav className="space-y-2">
                <a href="#core-tracking" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>1. Core Tracking</span>
                </a>
                <a href="#analytics-validation" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>2. Analytics & Validation</span>
                </a>
                <a href="#intelligence-layer" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>3. Intelligence Layer</span>
                </a>
                <a href="#integrations-outputs" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>4. Integrations & Outputs</span>
                </a>
                <a href="#personalization-controls" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>5. Personalization & Controls</span>
                </a>
                <a href="#november-2025-features" className="flex items-center gap-2 text-[--text] hover:text-[--primary] transition-colors">
                  <ChevronRight className="h-4 w-4" />
                  <span>6. November 2025 Features</span>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full ml-2">NEW</span>
                </a>
              </nav>
            </div>
          </div>

          {/* Section 1: Core Tracking */}
          <div id="core-tracking" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <BookOpen className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                1. Core Tracking
              </h2>
            </div>

            <div className="space-y-8">
              {/* Events Page */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Search className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Events Page</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Browse all market events with powerful filtering, search, and sorting capabilities. Each event displays impact scores, direction predictions, confidence ratings, and source links.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Daily market scanning to identify high-impact catalysts</li>
                    <li>Researching historical events for a specific company or sector</li>
                    <li>Finding events matching specific criteria (event type, score range, timeframe)</li>
                    <li>Verifying event details before making informed decisions</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Events tab in the dashboard</li>
                    <li>Use filters to narrow by ticker, event type (SEC 8-K, FDA, Earnings, etc.), date range, or sector</li>
                    <li>Sort by impact score, date, or confidence to prioritize</li>
                    <li>Click any event to see full details and the source URL</li>
                    <li>Click the source link to verify the original filing or announcement</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>High score + high confidence events are the most actionable signals</li>
                    <li>Always verify critical events by clicking the source link to read the original filing</li>
                  </ul>
                </div>
              </div>

              {/* Companies Page */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Building2 className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Companies Page</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> View company profiles with sector information, event counts, and complete event timelines. Click any company to see their full event history and projected price movements.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Researching a company's event history before making investment decisions</li>
                    <li>Understanding which companies have the most catalysts in your target sectors</li>
                    <li>Reviewing projected percentage moves based on historical event patterns</li>
                    <li>Identifying companies with recent high-impact events</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Companies tab in the dashboard</li>
                    <li>Browse the list or search for a specific ticker or company name</li>
                    <li>Click any company to open the detailed event timeline modal</li>
                    <li>Review the timeline to see all events sorted chronologically</li>
                    <li>Check projected percentage moves (1d/5d/20d) based on historical data</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Look for companies with frequent high-impact events as potential catalyst-rich plays</li>
                    <li>Use the event timeline to understand how a company typically responds to specific event types</li>
                  </ul>
                </div>
              </div>

              {/* Watchlist */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Star className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Watchlist</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Track specific tickers you care about with personal notes. See all recent events for your watchlist companies in one dedicated view, making it easy to stay on top of your core holdings.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Monitoring your portfolio holdings for new catalysts</li>
                    <li>Tracking potential investment targets you're researching</li>
                    <li>Following specific tickers in your area of expertise or interest</li>
                    <li>Maintaining personal notes and observations about each ticker</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Watchlist tab in the dashboard</li>
                    <li>Click "Add Ticker" and enter the stock symbol (e.g., AAPL)</li>
                    <li>Optionally add personal notes for context (e.g., "Awaiting FDA approval Q2 2025")</li>
                    <li>View all recent events for your watchlist tickers in one place</li>
                    <li>Remove tickers by clicking the remove icon when you're no longer interested</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Use notes to track your thesis for each ticker (e.g., "Earnings momentum play", "FDA catalyst")</li>
                    <li>Keep your watchlist focused (10-20 tickers) for maximum signal-to-noise ratio</li>
                  </ul>
                </div>
              </div>

              {/* Calendar View */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Calendar className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Calendar View
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Visualize events across a month-based calendar to identify busy catalyst weeks, plan trading strategies around event clusters, and never miss important dates.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Planning your trading calendar around major event weeks (e.g., earnings season)</li>
                    <li>Identifying event-heavy days that might cause market volatility</li>
                    <li>Coordinating multiple catalysts for portfolio positions</li>
                    <li>Avoiding overexposure during concentrated event periods</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Calendar tab in the dashboard (Pro plan required)</li>
                    <li>Browse the month view to see event counts per day</li>
                    <li>Click any day to see all events scheduled for that date</li>
                    <li>Use filters to show only specific event types or sectors</li>
                    <li>Navigate between months to plan weeks ahead</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Watch for days with multiple high-impact events—these often create significant market moves</li>
                    <li>Plan entries/exits around quiet event periods to reduce unexpected catalyst risk</li>
                  </ul>
                </div>
              </div>

              {/* Advanced Search */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Filter className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Advanced Search
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Build complex queries using AND/OR logic to find exactly the events you need. Combine multiple criteria like score ranges, event types, sectors, and date ranges for surgical precision.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Finding rare event combinations (e.g., "FDA approvals OR M&A in biotech with score &gt; 80")</li>
                    <li>Building custom event screens matching your specific trading strategy</li>
                    <li>Researching historical patterns with precise criteria</li>
                    <li>Exporting filtered datasets for offline analysis</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Click "Advanced Search" button in the Events tab (Pro plan required)</li>
                    <li>Add multiple criteria using the query builder (event type, sector, score, date)</li>
                    <li>Chain criteria with AND (all must match) or OR (any can match) operators</li>
                    <li>Preview results in real-time as you build your query</li>
                    <li>Save frequently-used queries for quick access later</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Save your best-performing queries to replicate successful screening strategies</li>
                    <li>Combine sector + event type filters to focus on your edge (e.g., "Tech earnings with score &gt; 70")</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Analytics & Validation */}
          <div id="analytics-validation" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <BarChart3 className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                2. Analytics & Validation
              </h2>
            </div>

            <div className="space-y-8">
              {/* Backtesting */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <TrendingUp className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Backtesting & Strategy Framework
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Build, test, and refine custom trading strategies based on event signals. Define entry/exit conditions, position sizing methods, and risk management rules. Run backtests against historical data with realistic P&L calculations. See{" "}
                  <Link href="/backtesting" className="text-[--primary] hover:underline">Backtesting page</Link> for full details.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Strategy Builder Features:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Entry Conditions:</strong> Event types, impact score thresholds, direction filters, ticker selection</li>
                    <li><strong>Exit Rules:</strong> Stop-loss and take-profit levels, time-based exits</li>
                    <li><strong>Position Sizing:</strong> Fixed size, percent of equity, or volatility-scaled methods</li>
                    <li><strong>Risk Management:</strong> Maximum positions per strategy, sector exposure limits</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Performance Metrics:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Returns:</strong> Total return, CAGR (Compound Annual Growth Rate)</li>
                    <li><strong>Risk-Adjusted:</strong> Sharpe ratio, Sortino ratio</li>
                    <li><strong>Drawdown:</strong> Maximum peak-to-trough decline</li>
                    <li><strong>Trade Stats:</strong> Win rate, expectancy, trade count</li>
                    <li><strong>Equity Curve:</strong> Interactive chart showing portfolio value over time</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Backtesting tab (Pro plan required)</li>
                    <li>Define entry conditions (event types, score thresholds, direction)</li>
                    <li>Set position sizing method and risk management rules</li>
                    <li>Select date range and run the backtest</li>
                    <li>Review performance metrics and trade-by-trade history</li>
                    <li>Iterate on strategy parameters to improve results</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Start with simple strategies (single event type, clear rules) before adding complexity</li>
                    <li>Focus on Sharpe ratio &gt; 1.0 for risk-adjusted performance</li>
                    <li>Watch max drawdown—aim for drawdown below 20% for sustainable strategies</li>
                    <li>Test across multiple time periods to avoid overfitting to specific market conditions</li>
                  </ul>
                </div>
              </div>

              {/* Event Correlation */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <GitCompare className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Event Correlation
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Visualize event timelines and discover patterns. See how events cluster together, identify leading indicators, and understand cause-effect relationships across companies and sectors.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Finding patterns like "Guidance updates often precede earnings beats"</li>
                    <li>Identifying sector-wide event waves (e.g., biotech FDA approval clusters)</li>
                    <li>Understanding how events in peer companies might predict your holdings</li>
                    <li>Spotting unusual event combinations that create outsized opportunities</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Correlation tab (Pro plan required)</li>
                    <li>Select companies, event types, or sectors to analyze</li>
                    <li>Review the timeline visualization showing event relationships</li>
                    <li>Look for recurring patterns or event sequences</li>
                    <li>Use insights to anticipate future event cascades</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Watch for event clustering in a sector—often signals broader industry shifts</li>
                    <li>Use correlation insights to build anticipatory positions before event cascades</li>
                  </ul>
                </div>
              </div>

              {/* Peer Comparison */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Users className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Peer Comparison
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Compare a company's events to similar companies in the same sector. Identify if a company has more/fewer catalysts than peers, stronger event impact patterns, or unique event characteristics.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Evaluating if a company is catalyst-rich or catalyst-poor vs. peers</li>
                    <li>Understanding relative event impact (does this company move more on earnings?)</li>
                    <li>Finding overlooked companies with similar event profiles to winners</li>
                    <li>Validating investment theses through peer benchmarking</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Click on any company in the Companies tab</li>
                    <li>Click "Compare to Peers" button in the company modal (Pro plan required)</li>
                    <li>Review peer companies in the same sector with similar market cap</li>
                    <li>Compare event counts, average impact scores, and event type distribution</li>
                    <li>Identify outliers or patterns unique to your target company</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Look for companies with fewer events but higher average scores—quality over quantity</li>
                    <li>Use peer benchmarks to spot undervalued names with similar catalyst profiles</li>
                  </ul>
                </div>
              </div>

              {/* Portfolio Risk Analysis */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <BarChart3 className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Portfolio Risk Analysis</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Upload your portfolio holdings via CSV to see upcoming events that could affect your positions. Calculate exposure by multiplying expected price moves by share quantity and current price.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Managing risk before earnings season or major event clusters</li>
                    <li>Quantifying potential P&L impact from upcoming catalysts</li>
                    <li>Identifying overexposure to specific event types or sectors</li>
                    <li>Planning hedges or position sizing adjustments before known events</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Portfolio tab in the dashboard</li>
                    <li>Upload a CSV file with columns: ticker, quantity (e.g., "AAPL,100")</li>
                    <li>Review upcoming events for all your holdings</li>
                    <li>See typical price moves (1d/5d/20d) based on historical event patterns</li>
                    <li>Calculate exposure: expected_move × quantity × current_price</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Upload your portfolio weekly to stay ahead of new catalysts</li>
                    <li>Watch for event-heavy weeks where multiple holdings have catalysts—consider trimming exposure</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Intelligence Layer */}
          <div id="intelligence-layer" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <Brain className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                3. Intelligence Layer
              </h2>
            </div>

            <div className="space-y-8">
              {/* RadarQuant AI Assistant */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Brain className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    RadarQuant AI Assistant
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> GPT-4 powered conversational assistant trained on Impact Radar's event database. Ask natural language questions about events, patterns, companies, and get intelligent analysis based on real data.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Quick analysis: "What were the highest impact FDA approvals last month?"</li>
                    <li>Pattern discovery: "Show me companies with back-to-back earnings beats"</li>
                    <li>Event context: "Explain why this M&A event has a score of 85"</li>
                    <li>Portfolio insights: "Which of my watchlist tickers have upcoming catalysts?"</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the RadarQuant tab (Pro plan required)</li>
                    <li>Type your question in natural language (no SQL or filters needed)</li>
                    <li>Review the AI's analysis and supporting data</li>
                    <li>Ask follow-up questions to drill deeper</li>
                    <li>Click cited events to see full details and verify sources</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Be specific in your questions (mention timeframes, sectors, event types)</li>
                    <li>Use RadarQuant to explore patterns you might miss with manual filtering</li>
                  </ul>
                </div>
              </div>

              {/* Market Echo Engine */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Zap className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Market Echo Engine
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> ML-enhanced impact scores using a dual-model ensemble (XGBoost + PyTorch neural network) that learns from real market outcomes. The system achieves <strong>64.6% directional accuracy</strong> on 1-day predictions across 1,490 verified outcomes. See{" "}
                  <Link href="/market-echo" className="text-[--primary] hover:underline">Market Echo page</Link> for full details.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Key Features:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Neural Network Ensemble:</strong> XGBoost and PyTorch neural network run in parallel with dynamic weighting based on 30-day accuracy</li>
                    <li><strong>Confidence Calibration:</strong> Platt scaling ensures probability estimates are well-calibrated</li>
                    <li><strong>Online Learning:</strong> Neural network updates incrementally from new market data</li>
                    <li><strong>Twitter/X Sentiment:</strong> Real-time social sentiment integration for additional context</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Verified Accuracy:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>1-Day:</strong> 64.6% directional accuracy</li>
                    <li><strong>5-Day:</strong> 51.7% directional accuracy</li>
                    <li><strong>20-Day:</strong> 51.7% directional accuracy</li>
                    <li><strong>Overall:</strong> 57.4% combined accuracy across all horizons</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How It Works:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Every event gets a base impact score from deterministic rules</li>
                    <li>Both XGBoost and neural network models estimate potential price impact</li>
                    <li>Model outputs are dynamically weighted by recent performance (softmax blend)</li>
                    <li>After 1/5/20 days, we measure real abnormal returns and update accuracy metrics</li>
                    <li>Daily retraining pipeline keeps models current with market conditions</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Focus on 1-day predictions which have the highest accuracy (64.6%)</li>
                    <li>Look for events with high ML confidence scores (70%+) for strongest signals</li>
                    <li>Market Echo retrains daily and the neural network learns continuously</li>
                  </ul>
                </div>
              </div>

              {/* Projector Charts */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <LineChart className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Projector Charts
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Interactive price charts with event markers overlaid. Visualize exactly when events occurred and how the stock price responded. Powered by lightweight-charts for fast, professional charting.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Validating if high-impact events actually moved the stock</li>
                    <li>Understanding price reaction timing (immediate vs. delayed)</li>
                    <li>Identifying event-driven trends vs. noise</li>
                    <li>Building intuition about event-to-price relationships</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Projector tab (Pro plan required)</li>
                    <li>Enter a ticker symbol to load the price chart</li>
                    <li>Event markers appear as colored icons on the chart timeline</li>
                    <li>Hover over markers to see event details (type, score, direction)</li>
                    <li>Zoom and pan to analyze specific timeframes or event clusters</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Look for event clusters that coincide with major trend changes</li>
                    <li>Use charts to validate backtesting results visually</li>
                  </ul>
                </div>
              </div>

              {/* Impact Scoring System */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Target className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Impact Scoring System</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Understand how impact scores (0-100) are calculated. The system blends deterministic rules (sector, event type, timing) with ML predictions from Market Echo Engine to produce final scores.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Score Components:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Event Type Weight:</strong> FDA approvals, M&A, earnings have different base impact levels</li>
                    <li><strong>Sector Multiplier:</strong> Biotech FDA events score higher than tech guidance updates</li>
                    <li><strong>Market Context:</strong> Volatility, market regime, recent price action adjustments</li>
                    <li><strong>Timing:</strong> Events near critical support/resistance levels get boosted</li>
                    <li><strong>ML Adjustment:</strong> Market Echo Engine nudges score ±20 based on learned patterns</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Interpret Scores:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>0-30:</strong> Low impact, noise-level events, unlikely to move price significantly</li>
                    <li><strong>31-60:</strong> Moderate impact, worth monitoring but not urgent</li>
                    <li><strong>61-80:</strong> High impact, actionable catalysts worth immediate attention</li>
                    <li><strong>81-100:</strong> Critical events, major catalysts with strong directional conviction</li>
                  </ul>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Combine high score (80+) with high confidence (85%+) for best signal quality</li>
                    <li>Watch for directional consistency—if multiple high-score events agree on direction, conviction is higher</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Section 4: Integrations & Outputs */}
          <div id="integrations-outputs" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <Code className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                4. Integrations & Outputs
              </h2>
            </div>

            <div className="space-y-8">
              {/* X.com Sentiment */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Twitter className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    X.com Sentiment Analysis
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Real-time Twitter sentiment analysis for events and tickers. See what the market is saying about catalysts as they happen, track sentiment shifts, and identify social momentum.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Gauging market reaction to just-announced events</li>
                    <li>Identifying early sentiment shifts before price moves</li>
                    <li>Monitoring social buzz for watchlist tickers</li>
                    <li>Spotting crowded trades or contrarian opportunities</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the X Feed tab (Pro plan required)</li>
                    <li>Filter by ticker or event type to see relevant social chatter</li>
                    <li>Review sentiment scores (positive/negative/neutral) and volume</li>
                    <li>Click through to see actual tweets and verify sentiment context</li>
                    <li>Watch for sentiment divergences from event scores (contrarian signals)</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>High positive sentiment + high impact event = strong confirmation</li>
                    <li>Negative sentiment on positive events may signal skepticism worth investigating</li>
                  </ul>
                </div>
              </div>

              {/* Live Tape */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Radio className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Live Tape</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Real-time WebSocket event streaming. See new market events the moment they're detected and scored. Perfect for active traders who need instant alerts.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Monitoring intraday for breaking events (FDA approvals, M&A announcements)</li>
                    <li>Getting first-mover advantage on time-sensitive catalysts</li>
                    <li>Watching specific tickers or sectors in real-time during market hours</li>
                    <li>Filtering noise with minimum score thresholds (e.g., only show 70+ events)</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Overview tab to see the Live Tape panel</li>
                    <li>Use filters to focus: ticker, event type, minimum score</li>
                    <li>Events stream in real-time as scanners detect them</li>
                    <li>Pause the feed to review events without missing new ones</li>
                    <li>Click any event to see full details and source link</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Set minimum score to 70+ to avoid noise and focus on actionable events</li>
                    <li>Filter by your watchlist tickers for maximum relevance</li>
                  </ul>
                </div>
              </div>

              {/* API Access */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Code className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">API Access</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> REST API with authentication for programmatic access. Integrate Impact Radar data into your own trading systems, research platforms, or automated workflows.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Building custom trading algorithms that consume event data</li>
                    <li>Integrating Impact Radar into existing research platforms</li>
                    <li>Automating workflows (e.g., "Pull events, analyze, send to Slack")</li>
                    <li>Backtesting strategies with historical event data</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to Account → API Keys to generate your key</li>
                    <li>Review API documentation at /docs/api for endpoints and schemas</li>
                    <li>Authenticate requests with your API key in the Authorization header</li>
                    <li>Query events, companies, scores, etc. via REST endpoints</li>
                    <li>Respect rate limits based on your plan tier (Pro: 10k/month, Enterprise: 100k/month)</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Use webhooks (if available) instead of polling to reduce API quota usage</li>
                    <li>Cache event data locally for offline analysis to minimize API calls</li>
                  </ul>
                </div>
              </div>

              {/* CSV Export */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <FileDown className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    CSV Export
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Export filtered event lists and portfolio analysis results to CSV format. Take data offline for custom analysis, Excel modeling, or record-keeping.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Creating custom spreadsheets for offline analysis</li>
                    <li>Building event databases for proprietary research</li>
                    <li>Sharing filtered event lists with team members or clients</li>
                    <li>Archiving historical snapshots for compliance or record-keeping</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Apply filters in the Events tab to narrow your dataset</li>
                    <li>Click "Export CSV" button (Pro plan required)</li>
                    <li>Download CSV file with columns: date, ticker, event_type, score, direction, confidence, source</li>
                    <li>Open in Excel, Google Sheets, or import into your analysis tools</li>
                    <li>Repeat for portfolio analysis to export exposure calculations</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Export monthly snapshots to track how prediction accuracy evolves over time</li>
                    <li>Use CSV exports to build custom pivot tables and analysis in Excel</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Section 5: Personalization & Controls */}
          <div id="personalization-controls" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <Settings className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                5. Personalization & Controls
              </h2>
            </div>

            <div className="space-y-8">
              {/* Custom Scoring Weights */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Sliders className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">
                    Custom Scoring Weights
                    <PlanBadge plan="Pro" />
                  </h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Adjust impact score weights by event type and sector to match your personal trading style. If you trade biotech FDA catalysts, boost FDA weights. If you ignore dividends, reduce their impact.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Customizing scores to match your sector expertise (e.g., biotech vs. tech)</li>
                    <li>De-emphasizing event types you don't trade (e.g., dividend announcements)</li>
                    <li>Amplifying catalysts you know drive your strategy (e.g., M&A in small-cap)</li>
                    <li>Building personalized event feeds that align with your edge</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to Account → Scoring Preferences (Pro plan required)</li>
                    <li>Adjust sliders for event type weights (FDA, Earnings, M&A, etc.)</li>
                    <li>Set sector multipliers (Biotech, Tech, Finance, etc.)</li>
                    <li>Preview how your custom weights change example events</li>
                    <li>Save preferences—all future scores use your custom weights</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Start conservatively—small weight adjustments (10-20%) are often enough</li>
                    <li>Use backtesting to validate if your custom weights improve prediction accuracy</li>
                  </ul>
                </div>
              </div>

              {/* Alerts & Notifications */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Bell className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Alerts & Notifications</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Set up email and in-app alerts with custom criteria. Get notified when high-impact events occur for your watchlist tickers, sectors, or event types—never miss important catalysts.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Staying updated on watchlist tickers without constant monitoring</li>
                    <li>Getting notified only for high-score events (e.g., 80+ impact)</li>
                    <li>Filtering by event type to focus on your strategy (e.g., only M&A alerts)</li>
                    <li>Monitoring sectors even when you're away from the platform</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Alerts tab in the dashboard</li>
                    <li>Click "Create Alert" to set up a new rule</li>
                    <li>Configure criteria: minimum score, event type, sector, tickers</li>
                    <li>Choose delivery method: email, in-app notification, or both</li>
                    <li>Enable/disable alerts anytime without deleting them</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Set different alerts for different strategies (intraday vs. swing vs. long-term)</li>
                    <li>Use high score thresholds (75+) to avoid alert fatigue from low-impact events</li>
                  </ul>
                </div>
              </div>

              {/* Scanner Status & Manual Scans */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Activity className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Scanner Status & Manual Scans</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Monitor all active scanners and their health. Manually trigger scans when you need immediate updates for specific data sources (SEC, FDA, earnings, etc.).
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">When to Use:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Checking if scanners are running properly and detecting events</li>
                    <li>Forcing an immediate scan after major market news breaks</li>
                    <li>Verifying scanner uptime and last successful scan times</li>
                    <li>Troubleshooting if you suspect missing events</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Scanners tab in the dashboard</li>
                    <li>Review scanner status: active, idle, last_run, events_found</li>
                    <li>Click "Queue Manual Scan" for any scanner to trigger immediate run</li>
                    <li>Rate limit: 1 manual scan per 2 minutes per scanner</li>
                    <li>Monitor scan progress and check for new events in Events tab</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Available Scanners:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li><strong>SEC EDGAR:</strong> 8-K, 10-K, 10-Q filings</li>
                    <li><strong>FDA Announcements:</strong> Drug approvals, clinical trials</li>
                    <li><strong>Earnings:</strong> Quarterly earnings releases</li>
                    <li><strong>Press Releases:</strong> Official company announcements</li>
                    <li><strong>M&A:</strong> Mergers and acquisitions</li>
                    <li><strong>Product Launches:</strong> New product releases</li>
                    <li><strong>Guidance:</strong> Forward guidance updates</li>
                    <li><strong>Dividends:</strong> Dividend and buyback announcements</li>
                  </ul>
                </div>
              </div>

              {/* Account Settings & Preferences */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Settings className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Account Settings & Preferences</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Manage your account, API keys, billing, and global preferences. Control how Impact Radar behaves and integrates with your workflow.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Available Settings:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>API Keys:</strong> Generate and manage API keys for programmatic access</li>
                    <li><strong>Billing:</strong> View plan details, usage quotas, and upgrade options</li>
                    <li><strong>Notification Preferences:</strong> Email frequency, in-app settings</li>
                    <li><strong>Scoring Preferences:</strong> Custom event weights and sector multipliers</li>
                    <li><strong>Profile:</strong> Email, password, account info</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Account tab in the dashboard</li>
                    <li>Browse sections: Profile, API Keys, Billing, Preferences</li>
                    <li>Update settings as needed (changes save automatically)</li>
                    <li>Review usage quotas to ensure you're within plan limits</li>
                    <li>Upgrade plan if you need more API calls, advanced features, or team seats</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>Rotate API keys regularly for security best practices</li>
                    <li>Monitor usage quotas to avoid hitting limits during critical trading periods</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Section 6: November 2025 Features */}
          <div id="november-2025-features" className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-green-500/10 text-green-400">
                <Zap className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                6. November 2025 Features
              </h2>
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">NEW</span>
            </div>

            <div className="space-y-8">
              {/* Trade Signals */}
              <div className="rounded-2xl border border-green-500/20 bg-green-500/5 p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Target className="h-5 w-5 text-green-400" />
                  <h3 className="text-xl font-semibold text-[--text]">Trade Signals</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Get AI-generated trade recommendations with precise entry/exit targets, stop-loss levels, take-profit targets, and position sizing based on event impact analysis.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Signal Components:</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="rounded-lg bg-black/20 p-3">
                      <DollarSign className="h-4 w-4 text-[--primary] mb-1" />
                      <div className="text-xs text-[--muted]">Entry Price</div>
                      <div className="text-sm font-semibold text-[--text]">Current market price</div>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <StopCircle className="h-4 w-4 text-red-400 mb-1" />
                      <div className="text-xs text-[--muted]">Stop Loss</div>
                      <div className="text-sm font-semibold text-[--text]">5% or 2x ATR below</div>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <Target className="h-4 w-4 text-green-400 mb-1" />
                      <div className="text-xs text-[--muted]">Take Profit</div>
                      <div className="text-sm font-semibold text-[--text]">Impact-scaled target</div>
                    </div>
                    <div className="rounded-lg bg-black/20 p-3">
                      <TrendingUp className="h-4 w-4 text-yellow-400 mb-1" />
                      <div className="text-xs text-[--muted]">R/R Ratio</div>
                      <div className="text-sm font-semibold text-[--text]">Risk vs reward</div>
                    </div>
                  </div>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Trade Signals tab in the dashboard</li>
                    <li>View all AI-generated signals or filter by "Portfolio" for your holdings</li>
                    <li>Click "Generate for Portfolio" to create signals based on your portfolio events</li>
                    <li>Review entry price, stop loss, take profit, and position sizing recommendations</li>
                    <li>Check the R/R ratio: green (2:1+) is favorable, yellow (1.5-2:1) acceptable, red (&lt;1.5:1) higher risk</li>
                  </ol>
                </div>
              </div>

              {/* Sector Analysis */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <PieChart className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Sector Analysis</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Track sector-level performance with rotation signals, momentum scoring, and capital flow analysis to identify market trends and sector opportunities.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Key Features:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Rotation Signals:</strong> Detect capital inflow/outflow between sectors</li>
                    <li><strong>Momentum Scoring:</strong> Track sector momentum using event-driven price changes</li>
                    <li><strong>Event Clustering:</strong> Identify when high-impact events concentrate in specific sectors</li>
                    <li><strong>Cross-Sector Correlation:</strong> Discover relationships between sectors and event types</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Sectors tab in the dashboard</li>
                    <li>Review sector performance cards showing momentum and rotation status</li>
                    <li>Look for "Inflow" indicators for sectors receiving capital</li>
                    <li>Check "Outflow" indicators for sectors losing capital</li>
                    <li>Click any sector to see detailed event analysis and trends</li>
                  </ol>
                </div>
              </div>

              {/* Model Explainability */}
              <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Brain className="h-5 w-5 text-blue-400" />
                  <h3 className="text-xl font-semibold text-[--text]">Model Explainability (SHAP)</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Understand exactly why the AI made each prediction with SHAP-based feature contribution visualizations. Full transparency into the decision-making process.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">What You See:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Feature Contributions:</strong> Which factors pushed the prediction higher or lower</li>
                    <li><strong>SHAP Values:</strong> Numeric impact of each feature on the final score</li>
                    <li><strong>Multi-Horizon:</strong> Explanations for 1-day, 7-day, and 30-day predictions</li>
                    <li><strong>Visual Charts:</strong> Bar charts showing positive (green) and negative (red) contributions</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Click on any event in the Events list to open details</li>
                    <li>Look for the "Explainability" or "Why This Score?" section</li>
                    <li>Toggle between 1d, 7d, and 30d horizons to see how factors change</li>
                    <li>Review which features had the most impact on the prediction</li>
                  </ol>
                </div>
              </div>

              {/* Historical Pattern Matching */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <History className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Historical Pattern Matching</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Find similar historical events and their outcomes. Learn from past market reactions to predict future price movements.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Key Features:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Pattern Library:</strong> Catalog of historical event patterns and outcomes</li>
                    <li><strong>Similar Event Lookup:</strong> Find events matching type, sector, and impact</li>
                    <li><strong>Outcome Tracking:</strong> See how similar events performed historically</li>
                    <li><strong>Success Rates:</strong> Statistical analysis of pattern reliability</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Open any event detail view</li>
                    <li>Look for "Similar Historical Events" section</li>
                    <li>Review matched events and their price outcomes</li>
                    <li>Use pattern statistics to inform your trading decisions</li>
                  </ol>
                </div>
              </div>

              {/* Custom Alert Rules */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Bell className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Custom Alert Rules</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Define your own alert thresholds with flexible conditions. Get notified when events match your specific criteria.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Condition Types:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Impact Score:</strong> Trigger when score is &gt;, &lt;, or = a threshold</li>
                    <li><strong>Sector Filter:</strong> Only alert for specific sectors</li>
                    <li><strong>Ticker Filter:</strong> Watch specific stocks</li>
                    <li><strong>Event Type:</strong> Focus on FDA, earnings, SEC filings, etc.</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the Alerts tab in the dashboard</li>
                    <li>Click "Create Custom Rule"</li>
                    <li>Define your condition (e.g., "Impact Score &gt; 75")</li>
                    <li>Add optional filters (sector, ticker, event type)</li>
                    <li>Choose notification method (email, in-app, or both)</li>
                    <li>Save and enable the rule</li>
                  </ol>
                </div>
              </div>

              {/* Email Digests */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Mail className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Email Digests</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Subscribe to daily or weekly email summaries with configurable content sections. Stay informed without dashboard fatigue.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Digest Options:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Daily Digest:</strong> Morning summary of previous day's events</li>
                    <li><strong>Weekly Digest:</strong> Weekend recap of the week's highlights</li>
                    <li><strong>Custom Sections:</strong> Choose what content to include</li>
                    <li><strong>Watchlist Focus:</strong> Prioritize your watched tickers</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Go to Settings → Notifications</li>
                    <li>Enable email digests</li>
                    <li>Choose frequency (daily or weekly)</li>
                    <li>Configure content sections to include</li>
                    <li>Set preferred delivery time</li>
                  </ol>
                </div>
              </div>

              {/* CSV Export */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <FileDown className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">CSV Export</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Export event data and portfolio analysis in CSV format for offline analysis, reporting, or integration with your existing tools.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Export Options:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Events Export:</strong> All event data with scores, dates, and metadata</li>
                    <li><strong>Portfolio Export:</strong> Your portfolio analysis and event exposure</li>
                    <li><strong>Custom Date Ranges:</strong> Export specific time periods</li>
                    <li><strong>Filtered Exports:</strong> Export only filtered results</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to Events or Portfolio tab</li>
                    <li>Apply any filters you want to include</li>
                    <li>Click the "Export CSV" button</li>
                    <li>Download opens automatically</li>
                    <li>Import into Excel, Google Sheets, or your analysis tool</li>
                  </ol>
                </div>
              </div>

              {/* Saved Filters & Preferences */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Save className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Saved Filters & Preferences</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Save your favorite filter combinations and dashboard settings. Your preferences persist across sessions for a personalized experience.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">What You Can Save:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Filter Combinations:</strong> Event type + sector + score range</li>
                    <li><strong>Dashboard Layout:</strong> Tab preferences and default views</li>
                    <li><strong>Quick Filters:</strong> One-click access to saved searches</li>
                    <li><strong>Column Preferences:</strong> Which columns to show in tables</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Configure your preferred filters in any view</li>
                    <li>Click "Save Filter" to store the combination</li>
                    <li>Name your saved filter for easy identification</li>
                    <li>Access saved filters from the filter dropdown</li>
                    <li>Manage saved filters in Settings → Preferences</li>
                  </ol>
                </div>
              </div>

              {/* Dark/Light Mode */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Palette className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Dark/Light Mode</h3>
                  <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">NEW</span>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Purpose:</strong> Toggle between dark and light themes to match your preference. System-aware mode automatically adapts to your device settings.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Theme Options:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong>Dark Mode:</strong> Default theme, optimized for low-light environments</li>
                    <li><strong>Light Mode:</strong> Bright theme for daytime use</li>
                    <li><strong>System Mode:</strong> Automatically matches your OS preference</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Use:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Go to Settings tab in the dashboard</li>
                    <li>Find the "Theme" section</li>
                    <li>Select Dark, Light, or System</li>
                    <li>Theme changes apply instantly</li>
                    <li>Your preference is saved for future sessions</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>

          {/* Understanding Impact Scores */}
          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Understanding Impact Scores
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Every event gets three key metrics to help you assess significance and reliability:
              </p>
              <div className="space-y-6">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Target className="h-5 w-5 text-[--primary]" />
                    <h3 className="text-lg font-semibold text-[--text]">Impact Score (0-100)</h3>
                  </div>
                  <p className="text-sm text-[--muted] ml-7">
                    How significant the event is for the stock price. Higher scores mean bigger potential impact. Calculated using event type weights, sector multipliers, market context, timing, and ML adjustments from Market Echo Engine.
                  </p>
                  <div className="mt-3 ml-7 grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="rounded-lg bg-gray-500/10 p-3">
                      <div className="text-xs text-[--muted] mb-1">Low Impact</div>
                      <div className="text-lg font-bold text-gray-400">0-30</div>
                    </div>
                    <div className="rounded-lg bg-blue-500/10 p-3">
                      <div className="text-xs text-[--muted] mb-1">Moderate</div>
                      <div className="text-lg font-bold text-blue-400">31-60</div>
                    </div>
                    <div className="rounded-lg bg-yellow-500/10 p-3">
                      <div className="text-xs text-[--muted] mb-1">High Impact</div>
                      <div className="text-lg font-bold text-yellow-400">61-80</div>
                    </div>
                    <div className="rounded-lg bg-green-500/10 p-3">
                      <div className="text-xs text-[--muted] mb-1">Critical</div>
                      <div className="text-lg font-bold text-green-400">81-100</div>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="h-5 w-5 text-[--primary]" />
                    <h3 className="text-lg font-semibold text-[--text]">Direction</h3>
                  </div>
                  <p className="text-sm text-[--muted] ml-7">
                    Whether the event is likely positive (bullish), negative (bearish), neutral, or uncertain for the stock price. Based on event semantics, historical patterns, and ML predictions.
                  </p>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="h-5 w-5 text-[--primary]" />
                    <h3 className="text-lg font-semibold text-[--text]">Confidence (0-100%)</h3>
                  </div>
                  <p className="text-sm text-[--muted] ml-7">
                    How confident the system is about the impact score and direction. Higher confidence means the prediction is more reliable based on historical patterns and data quality. Events with 85%+ confidence have proven most accurate in backtesting.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Plans & Pricing */}
          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Plans & Features
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Impact Radar offers different plans to match your needs:
              </p>
              <div className="space-y-4">
                <div className="rounded-xl border border-white/10 bg-[--background] p-4">
                  <h3 className="text-lg font-semibold text-[--text] mb-2">Free Plan</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Limited event history (30 days)</li>
                    <li>Basic filtering and search</li>
                    <li>Impact scores and source links</li>
                    <li>Watchlist (up to 10 tickers)</li>
                    <li>Live Tape with basic filters</li>
                  </ul>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Pro Plan
                    <span className="ml-2 text-sm font-normal text-[--primary]">Most Popular</span>
                  </h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Full event history (unlimited)</li>
                    <li>Advanced search with AND/OR logic</li>
                    <li>Calendar view and backtesting</li>
                    <li>RadarQuant AI Assistant</li>
                    <li>Market Echo ML-enhanced scores</li>
                    <li>Projector charts with event markers</li>
                    <li>X.com sentiment analysis</li>
                    <li>Custom scoring weights</li>
                    <li>Portfolio risk analysis</li>
                    <li>CSV export</li>
                    <li>API access (10k requests/month)</li>
                    <li>Email + in-app alerts</li>
                  </ul>
                </div>

                <div className="rounded-xl border border-white/10 bg-[--background] p-4">
                  <h3 className="text-lg font-semibold text-[--text] mb-2">Enterprise Plan</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Everything in Pro</li>
                    <li>Team collaboration features</li>
                    <li>API access (100k requests/month)</li>
                    <li>Priority support</li>
                    <li>Custom integrations</li>
                    <li>Dedicated account manager</li>
                  </ul>
                </div>
              </div>
              <div className="mt-6 text-center">
                <Link 
                  href="/pricing" 
                  className="inline-flex items-center gap-2 text-[--primary] hover:underline"
                >
                  View Full Pricing Details
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>

          {/* CTA Section */}
          <div className="mt-24 max-w-4xl mx-auto">
            <div className="rounded-3xl border border-[--primary]/20 bg-[--primary]/5 p-8 text-center">
              <h2 className="text-2xl font-semibold text-[--text] mb-4">
                Ready to Start Tracking Market Events?
              </h2>
              <p className="text-[--muted] mb-6">
                Sign up for free or explore Pro features with a 7-day trial. No credit card required.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link 
                  href="/dashboard" 
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-[--primary] hover:bg-[--primary]/90 text-white rounded-lg font-medium transition-colors"
                >
                  Go to Dashboard
                  <ChevronRight className="h-4 w-4" />
                </Link>
                <Link 
                  href="/pricing" 
                  className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-white/10 hover:border-white/20 text-[--text] rounded-lg font-medium transition-colors"
                >
                  View Pricing
                </Link>
              </div>
            </div>
          </div>

          {/* Subscription Management */}
          <div className="mt-24 max-w-5xl mx-auto">
            <div className="flex items-center gap-3 mb-8">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                <Settings className="h-6 w-6" />
              </div>
              <h2 className="text-3xl font-semibold text-[--text]">
                Managing Your Subscription
              </h2>
            </div>

            <div className="space-y-8">
              {/* Upgrading Your Plan */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <TrendingUp className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">How to Upgrade Your Plan</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Upgrading unlocks:</strong> Advanced analytics, backtesting, RadarQuant AI assistant, unlimited alerts, API access, and more.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Upgrade Options:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Navigate to the <Link href="/dashboard" className="text-[--primary] hover:underline">Dashboard</Link> and click the "Upgrade Plan" button</li>
                    <li>Or visit the <Link href="/pricing" className="text-[--primary] hover:underline">Pricing Page</Link> to compare plans and select one</li>
                    <li>In your Account tab, click on your Plan card to manage your subscription</li>
                    <li>Choose between Pro ($49/month) or Enterprise (custom pricing)</li>
                    <li>Complete payment through our secure Stripe checkout</li>
                    <li>Your upgrade takes effect immediately with full feature access</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Pro Tips:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-[--muted] ml-4">
                    <li>New Pro subscribers get a 7-day free trial—no credit card required upfront</li>
                    <li>Billing is monthly with no long-term contracts. Cancel anytime.</li>
                    <li>Enterprise plans include team features and dedicated support—contact us for pricing</li>
                  </ul>
                </div>
              </div>

              {/* Canceling Your Subscription */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <Activity className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">How to Cancel Your Subscription</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">We're sorry to see you go!</strong> You can cancel your subscription anytime. You'll retain access to premium features until the end of your current billing period.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">How to Cancel:</h4>
                  <ol className="list-decimal list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li>Go to the <Link href="/dashboard" className="text-[--primary] hover:underline">Dashboard</Link> and navigate to the Account tab</li>
                    <li>Click on your Plan card or scroll to the Account Management section</li>
                    <li>Click the "Cancel Subscription" button</li>
                    <li>Review what you'll lose access to after cancellation</li>
                    <li>Confirm cancellation</li>
                    <li>You'll receive a confirmation email with your final access date</li>
                  </ol>
                </div>

                <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4">
                  <h4 className="text-sm font-semibold text-yellow-400 mb-2">What Happens After Cancellation:</h4>
                  <ul className="list-disc list-inside space-y-1 text-xs text-yellow-300 ml-4">
                    <li>Your account remains active until the end of your billing period</li>
                    <li>After that, you'll revert to the Free plan with limited features</li>
                    <li>Your watchlist and account data are preserved—you can re-upgrade anytime</li>
                    <li>No refunds for partial months, but no charges after cancellation</li>
                  </ul>
                </div>
              </div>

              {/* Billing and Payment Management */}
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-8">
                <div className="flex items-center gap-3 mb-4">
                  <CreditCard className="h-5 w-5 text-[--primary]" />
                  <h3 className="text-xl font-semibold text-[--text]">Billing and Payment Management</h3>
                </div>
                
                <p className="text-[--muted] mb-4">
                  <strong className="text-[--text]">Manage your payment methods and billing history</strong> through your account settings or the Stripe customer portal.
                </p>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Payment Management:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-[--muted] ml-4">
                    <li><strong className="text-[--text]">Update Payment Method:</strong> Go to Account → Plan card → Manage Subscription to access the Stripe portal</li>
                    <li><strong className="text-[--text]">View Billing History:</strong> Access past invoices and receipts in the Stripe customer portal</li>
                    <li><strong className="text-[--text]">Change Billing Cycle:</strong> Contact support to switch between monthly and annual billing</li>
                    <li><strong className="text-[--text]">Failed Payments:</strong> You'll receive email notifications. Update your payment method to restore access</li>
                  </ul>
                </div>

                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-[--text] mb-2">Common Questions:</h4>
                  <div className="space-y-3 text-sm">
                    <div>
                      <p className="text-[--text] font-medium">Q: When am I billed?</p>
                      <p className="text-[--muted] ml-4">A: Billing occurs monthly on the date you first subscribed. You'll receive an invoice via email.</p>
                    </div>
                    <div>
                      <p className="text-[--text] font-medium">Q: Can I get a refund?</p>
                      <p className="text-[--muted] ml-4">A: We offer refunds within 7 days of purchase if you're not satisfied. Contact support@impactradar.com.</p>
                    </div>
                    <div>
                      <p className="text-[--text] font-medium">Q: Do you offer annual billing?</p>
                      <p className="text-[--muted] ml-4">A: Yes! Annual plans are available with a discount. Contact us for details.</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                  <h4 className="text-sm font-semibold text-green-400 mb-2">Need Help?</h4>
                  <p className="text-xs text-green-300">
                    Have billing questions or issues? Email us at <a href="mailto:support@impactradar.com" className="underline">support@impactradar.com</a> or reach out through the in-app support chat.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Final Tips */}
          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-6">
              <div className="flex gap-4">
                <Lightbulb className="h-6 w-6 text-yellow-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Final Pro Tips for Success
                  </h3>
                  <ul className="space-y-2 text-sm text-[--muted]">
                    <li>✓ Check the Live Tape first thing each morning to catch overnight events</li>
                    <li>✓ Set alerts for your watchlist tickers so you never miss important catalysts</li>
                    <li>✓ Always click source links to verify events before making informed decisions</li>
                    <li>✓ High impact scores (80+) combined with high confidence (85%+) are the most actionable</li>
                    <li>✓ Upload your portfolio weekly to stay ahead of upcoming catalysts</li>
                    <li>✓ Use backtesting to validate which event types work best for your strategy</li>
                    <li>✓ Filter by your sector expertise to maximize signal-to-noise ratio</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
