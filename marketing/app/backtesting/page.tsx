import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Database, Calculator, TrendingUp, CheckCircle2, BarChart3, FileText, Activity, Beaker, Building2, Radio, Target, Lightbulb, AlertTriangle, Sliders, Shield, LineChart, Brain, StopCircle, DollarSign, Percent } from "lucide-react";

const dataCollectionPhases = [
  {
    icon: <Radio className="h-6 w-6" />,
    phase: "Phase 1",
    title: "Data Collection",
    description:
      "11 automated scanners monitor SEC filings (8-K, 10-Q, EDGAR), FDA announcements, earnings calls, M&A activity, guidance updates, dividends/buybacks, product launches, press releases, and Form 4 insider trading. Events include source attribution and timestamps.",
  },
  {
    icon: <Target className="h-6 w-6" />,
    phase: "Phase 2",
    title: "Impact Scoring",
    description:
      "Each event receives a deterministic impact score (0-100) using quantitative rules. This base score considers event type, historical patterns, sector context, and market conditions.",
  },
  {
    icon: <Activity className="h-6 w-6" />,
    phase: "Phase 3",
    title: "Price Tracking",
    description:
      "We track actual stock price movements at 1-day (64.6% accuracy), 5-day (51.7% accuracy), and 20-day (51.7% accuracy) horizons. Benchmark returns (SPY) are calculated to isolate event-specific impact from general market movements.",
  },
  {
    icon: <TrendingUp className="h-6 w-6" />,
    phase: "Phase 4",
    title: "Outcome Validation",
    description:
      "After sufficient time has passed, we calculate the actual returns and compare them to our predictions. This data trains the Market Echo Engine to improve future predictions.",
  },
];

const dataSources = [
  {
    icon: <FileText className="h-6 w-6" />,
    title: "SEC EDGAR Filings",
    description:
      "Automated scanning of SEC 8-K current reports capturing material events like M&A, executive changes, material agreements, and regulatory updates. Additional SEC filing types are being integrated.",
  },
  {
    icon: <Beaker className="h-6 w-6" />,
    title: "FDA Announcements",
    description:
      "We monitor FDA drug approvals, rejections, clinical trial results, and regulatory actions. These events have high impact for biotech and pharmaceutical companies.",
  },
  {
    icon: <Building2 className="h-6 w-6" />,
    title: "Additional Event Sources",
    description:
      "Targeted coverage of corporate announcements including product launches, partnership agreements, and strategic initiatives. Coverage is expanding as the platform matures.",
  },
];

const quantitativeFormulas = [
  {
    formula: "Raw Return",
    calculation: "((price_after - price_before) / price_before) × 100",
    description: "Simple percentage change in stock price over the specified horizon (1d, 5d, or 20d).",
    example: "If stock moves from $100 to $108, raw return = +8%",
  },
  {
    formula: "Benchmark Return",
    calculation: "((spy_after - spy_before) / spy_before) × 100",
    description: "S&P 500 (SPY) return over the same period, representing general market movement.",
    example: "If SPY moves from $450 to $459, benchmark return = +2%",
  },
  {
    formula: "Abnormal Return",
    calculation: "return_pct = return_pct_raw - benchmark_return_pct",
    description: "The event-specific impact after removing market noise. This is our primary target metric for ML training.",
    example: "Stock return (+8%) - Market return (+2%) = Abnormal return (+6%)",
  },
  {
    formula: "Direction Accuracy",
    calculation: "predicted_direction == actual_direction",
    description: "Binary check: did we correctly predict if the stock would move up or down?",
    example: "Predicted 'bullish', stock went up (+6%) → Correct ✓",
  },
];

const marketEchoIntegration = [
  "EventOutcome data serves as ground truth labels for training ML models",
  "Market Echo Engine learns which event types, sectors, and market conditions lead to stronger/weaker moves",
  "When Market Echo Engine makes a prediction, it stores ml_adjusted_score on the event record",
  "Backtesting engine uses ML predictions (ml_adjusted_score) when available, otherwise uses deterministic scoring (impact_score)",
  "Accuracy dashboard tracks performance across 3 model versions: v1.0-deterministic, v1.5-ml-hybrid, v2.0-market-echo",
  "Continuous learning pipeline: new outcomes → model retraining → improved predictions",
];

const strategyFeatures = [
  {
    icon: <Sliders className="h-6 w-6" />,
    title: "Strategy Builder",
    description:
      "Define custom entry conditions based on event types, impact score thresholds, direction filters, and ticker selection. Build strategies that match your trading style.",
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: "Risk Management",
    description:
      "Set stop-loss and take-profit levels, choose position sizing methods (fixed, percent of equity, volatility-scaled), and define maximum positions per strategy.",
  },
  {
    icon: <LineChart className="h-6 w-6" />,
    title: "Performance Metrics",
    description:
      "Comprehensive metrics including Sharpe ratio, Sortino ratio, CAGR, max drawdown, win rate, expectancy, and detailed trade-by-trade history.",
  },
];

const positionSizingMethods = [
  {
    method: "Fixed Size",
    description: "Use a constant dollar amount per trade regardless of equity or volatility",
    example: "$10,000 per position",
  },
  {
    method: "Percent of Equity",
    description: "Risk a percentage of current portfolio value on each trade",
    example: "2% of equity per trade",
  },
  {
    method: "Volatility-Scaled",
    description: "Adjust position size based on the asset's volatility (ATR-based)",
    example: "Scale position inversely to 20-day ATR",
  },
];

const performanceMetrics = [
  "Total Return: Overall profit/loss as percentage of starting capital",
  "CAGR: Compound Annual Growth Rate normalized for time period",
  "Sharpe Ratio: Risk-adjusted return measuring excess return per unit of volatility",
  "Sortino Ratio: Like Sharpe but only penalizes downside volatility",
  "Max Drawdown: Largest peak-to-trough decline during the backtest period",
  "Win Rate: Percentage of trades that were profitable",
  "Expectancy: Average expected gain per trade accounting for win rate and average win/loss",
  "Trade Count: Total number of trades executed in the backtest period",
];

const technicalHighlights = [
  {
    metric: "11",
    label: "Event Family Types",
    description: "SEC 8-K/10-Q/10-K, FDA, Earnings, M&A, Guidance, Dividends, Product Launches, Insider Trading, and more",
  },
  {
    metric: "3",
    label: "Time Horizons",
    description: "1-day (64.6%), 5-day (51.7%), and 20-day (51.7%) price movement tracking when historical data is available",
  },
  {
    metric: "11",
    label: "Automated Scanners",
    description: "SEC EDGAR, SEC 8-K, SEC 10-Q, FDA, Earnings, M&A, Guidance, Product Launch, Dividends, Press, Form 4 Insider",
  },
  {
    metric: "1,490+",
    label: "Validated Outcomes",
    description: "Events with verified price movements across all scanner types, growing daily",
  },
];

export default function BacktestingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Backtesting <span className="text-[--primary]">Methodology</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              How we collect event data, calculate real outcomes, and validate predictions. Outcome calculations are based on verified stock price movements from public market data.
            </p>
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-6">
              <div className="flex gap-4">
                <Database className="h-6 w-6 text-blue-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Real Data, Not Mock Data
                  </h3>
                  <p className="text-sm text-[--muted] mb-2">
                    Impact Radar uses real historical event data and verified stock price movements. We do not use simulated or fabricated data. Events are sourced primarily from SEC EDGAR filings and FDA announcements, with additional event types being integrated as the platform expands.
                  </p>
                  <p className="text-sm text-[--muted]">
                    All price data comes from public market data APIs, and all return calculations are computed using the exact formulas shown on this page. This ensures complete transparency and reproducibility.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-orange-500/20 bg-orange-500/5 p-6">
              <div className="flex gap-4">
                <AlertTriangle className="h-6 w-6 text-orange-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Coverage Status
                  </h3>
                  <p className="text-sm text-[--muted] mb-2">
                    <strong>Primary Coverage:</strong> SEC 8-K filings, FDA announcements, earnings, and more are continuously monitored with automated ingestion and scoring. Approximately <strong>1,490+ events across 440+ tickers</strong> have been validated with verified price outcomes.
                  </p>
                  <p className="text-sm text-[--muted] mb-2">
                    <strong>Expanding Coverage:</strong> Additional event types (earnings, M&A, guidance updates, dividends, analyst ratings, corporate announcements) are being integrated incrementally. Coverage breadth is prototype-level and expanding as the platform matures.
                  </p>
                  <p className="text-sm text-orange-300/90">
                    <strong>Important:</strong> Impact Radar is a research and analysis tool. All predictions, scores, and analytics are designed for educational and analytical purposes, not investment advice or guarantees. Always conduct your own due diligence and consult with qualified financial professionals before making investment decisions.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {dataCollectionPhases.map((phase) => (
              <div
                key={phase.phase}
                className="rounded-2xl border border-white/10 bg-[--panel] p-6"
              >
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                  {phase.icon}
                </div>
                <div className="text-xs font-semibold text-[--primary] mb-2">
                  {phase.phase}
                </div>
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  {phase.title}
                </h3>
                <p className="text-sm text-[--muted]">{phase.description}</p>
              </div>
            ))}
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Data Sources
            </h2>
            <div className="grid gap-6 md:grid-cols-3">
              {dataSources.map((source) => (
                <div
                  key={source.title}
                  className="rounded-2xl border border-white/10 bg-[--panel] p-6"
                >
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                    {source.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    {source.title}
                  </h3>
                  <p className="text-sm text-[--muted]">{source.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Quantitative Formulas
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Every EventOutcome record is calculated using these deterministic formulas. There is no AI or estimation involved in these calculations—they are pure mathematics applied to real price data.
              </p>
              <div className="space-y-6">
                {quantitativeFormulas.map((item) => (
                  <div
                    key={item.formula}
                    className="border-l-4 border-[--primary] pl-6"
                  >
                    <h3 className="text-lg font-semibold text-[--text] mb-2">
                      {item.formula}
                    </h3>
                    <div className="font-mono text-sm text-[--accent] bg-black/20 rounded px-3 py-2 mb-2">
                      {item.calculation}
                    </div>
                    <p className="text-sm text-[--muted] mb-2">
                      {item.description}
                    </p>
                    <div className="text-sm text-[--text] bg-green-500/5 border border-green-500/20 rounded px-3 py-2">
                      <strong>Example:</strong> {item.example}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Market Echo Engine Integration
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                The quantitative formulas above generate EventOutcome data, which serves as the ground truth for training the Market Echo Engine. Here's how the two systems work together:
              </p>
              <ul className="space-y-4">
                {marketEchoIntegration.map((point) => (
                  <li key={point} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{point}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Key Insight:</span> EventOutcome data is created with quantitative formulas (deterministic, reproducible, transparent). The Market Echo Engine uses this data as training labels to learn better predictions. When ML predictions are available, the system uses ml_adjusted_score; otherwise it falls back to the deterministic impact_score. Formulas provide truth, AI learns to improve predictions.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Strategy Framework
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8 mb-8">
              <p className="text-[--muted] mb-6">
                Build, test, and refine custom trading strategies based on event signals. The backtesting framework supports comprehensive strategy definition with entry/exit rules, position sizing, and risk management.
              </p>
              <div className="grid gap-6 md:grid-cols-3">
                {strategyFeatures.map((feature) => (
                  <div
                    key={feature.title}
                    className="rounded-xl border border-white/5 bg-white/5 p-4"
                  >
                    <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-[--primary]/10 text-[--primary] mb-3">
                      {feature.icon}
                    </div>
                    <h4 className="text-sm font-semibold text-[--text] mb-2">
                      {feature.title}
                    </h4>
                    <p className="text-xs text-[--muted]">{feature.description}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Position Sizing Methods
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Choose how your strategy allocates capital to each trade. Different methods suit different risk tolerances and market conditions.
              </p>
              <div className="space-y-4">
                {positionSizingMethods.map((item) => (
                  <div
                    key={item.method}
                    className="border-l-4 border-[--primary] pl-6"
                  >
                    <h3 className="text-lg font-semibold text-[--text] mb-2">
                      {item.method}
                    </h3>
                    <p className="text-sm text-[--muted] mb-2">
                      {item.description}
                    </p>
                    <div className="text-sm text-[--text] bg-green-500/5 border border-green-500/20 rounded px-3 py-2">
                      <strong>Example:</strong> {item.example}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Performance Metrics
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                Comprehensive metrics to evaluate your strategy's performance. All calculations follow industry-standard methodologies.
              </p>
              <ul className="space-y-3">
                {performanceMetrics.map((metric) => (
                  <li key={metric} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{metric}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Equity Curve:</span> Track your strategy's performance over time with interactive equity curve charts. See exactly how your portfolio value changes with each trade.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Technical Highlights
            </h2>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {technicalHighlights.map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-white/10 bg-[--panel] p-6 text-center"
                >
                  <div className="text-4xl font-bold text-[--primary] mb-2">
                    {item.metric}
                  </div>
                  <div className="text-sm font-semibold text-[--text] mb-2">
                    {item.label}
                  </div>
                  <p className="text-xs text-[--muted]">{item.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Complete Example Workflow
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Step 1: Event Detection
                  </h3>
                  <p className="text-[--muted]">
                    SEC scanner detects an 8-K filing for ACME Corp (ACME) announcing a major partnership agreement on November 15, 2025 at 2:30 PM ET. Deterministic scoring engine assigns impact_score=72 with direction="bullish".
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Step 2: ML Enhancement (Optional)
                  </h3>
                  <p className="text-[--muted]">
                    Market Echo Engine reviews the event and stores ml_adjusted_score=78 based on historical partnership announcements in this sector. The system uses this ML prediction (78) when displaying the event to users with Pro or Enterprise plans.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Step 3: Price Tracking
                  </h3>
                  <p className="text-[--muted]">
                    System records: price_before=$50.00 (Nov 15), price_after_1d=$53.50 (Nov 16), price_after_5d=$54.75 (Nov 22). SPY moved from $450 to $452.70 (+0.6%) over the same 5-day period.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Step 4: Outcome Calculation
                  </h3>
                  <p className="text-[--muted] mb-3">
                    OutcomeLabeler runs on November 23, 2025 and calculates:
                  </p>
                  <div className="space-y-2 text-sm font-mono bg-black/20 rounded p-4">
                    <div>return_pct_raw_5d = ((54.75 - 50.00) / 50.00) × 100 = <span className="text-green-400">+9.5%</span></div>
                    <div>benchmark_return_pct_5d = ((452.70 - 450.00) / 450.00) × 100 = <span className="text-blue-400">+0.6%</span></div>
                    <div>return_pct_5d = 9.5% - 0.6% = <span className="text-[--accent]">+8.9% abnormal return</span></div>
                    <div>direction_correct = true (predicted bullish, actual +8.9%)</div>
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Step 5: Learning & Improvement
                  </h3>
                  <p className="text-[--muted]">
                    This EventOutcome record (+8.9% abnormal return) is added to the training dataset. Market Echo Engine learns that partnership announcements in this sector tend to outperform the base model's predictions. Next time a similar event occurs, the AI will make a more calibrated prediction.
                  </p>
                </div>
                <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-[--text] mb-1">
                        Result: Validated Prediction
                      </p>
                      <p className="text-sm text-[--muted]">
                        The prediction was directionally correct (bullish) and the magnitude was strong (+8.9% abnormal return vs. 78/100 impact score). This outcome validates the model and helps improve future predictions for similar events.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Trade Signal Generation
            </h2>
            <div className="rounded-3xl border border-green-500/20 bg-green-500/5 p-8 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-green-500/10 text-green-400">
                  <Target className="h-6 w-6" />
                </div>
                <div>
                  <span className="text-xs font-semibold bg-green-500/20 text-green-400 px-2 py-1 rounded-full">NEW</span>
                  <h3 className="text-xl font-semibold text-[--text] mt-1">AI-Generated Trade Recommendations</h3>
                </div>
              </div>
              <p className="text-[--muted] mb-6">
                Building on our backtesting methodology, the Trade Signal system transforms validated event predictions into actionable trade recommendations with precise entry/exit targets.
              </p>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
                <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                  <DollarSign className="h-5 w-5 text-[--primary] mb-2" />
                  <h4 className="text-sm font-semibold text-[--text] mb-1">Entry Price</h4>
                  <p className="text-xs text-[--muted]">Current market price at signal generation</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                  <StopCircle className="h-5 w-5 text-red-400 mb-2" />
                  <h4 className="text-sm font-semibold text-[--text] mb-1">Stop Loss</h4>
                  <p className="text-xs text-[--muted]">5% below entry or 2x ATR for volatility-adjusted protection</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                  <Target className="h-5 w-5 text-green-400 mb-2" />
                  <h4 className="text-sm font-semibold text-[--text] mb-1">Take Profit</h4>
                  <p className="text-xs text-[--muted]">Calculated from stop distance x impact multiplier x 1.5</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                  <Percent className="h-5 w-5 text-yellow-400 mb-2" />
                  <h4 className="text-sm font-semibold text-[--text] mb-1">Position Size</h4>
                  <p className="text-xs text-[--muted]">1-5% of portfolio based on confidence level</p>
                </div>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/5 p-4">
                <h4 className="text-sm font-semibold text-[--text] mb-2">Risk/Reward Calculation</h4>
                <div className="font-mono text-sm text-[--accent] bg-black/20 rounded px-3 py-2 mb-2">
                  R/R Ratio = (take_profit - entry_price) / (entry_price - stop_loss)
                </div>
                <p className="text-xs text-[--muted]">
                  Signals with R/R ratios above 2:1 are highlighted in green, 1.5-2:1 in yellow, below 1.5:1 in red.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Model Explainability (SHAP)
            </h2>
            <div className="rounded-3xl border border-blue-500/20 bg-blue-500/5 p-8 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/10 text-blue-400">
                  <Brain className="h-6 w-6" />
                </div>
                <div>
                  <span className="text-xs font-semibold bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">NEW</span>
                  <h3 className="text-xl font-semibold text-[--text] mt-1">SHAP-Based Feature Contributions</h3>
                </div>
              </div>
              <p className="text-[--muted] mb-6">
                Every prediction from the Market Echo Engine now includes SHAP (SHapley Additive exPlanations) values that show exactly which features contributed to the prediction and by how much.
              </p>
              <div className="space-y-4 mb-6">
                <div className="border-l-4 border-blue-400 pl-6">
                  <h4 className="text-lg font-semibold text-[--text] mb-2">What is SHAP?</h4>
                  <p className="text-sm text-[--muted]">
                    SHAP is a game-theoretic approach to explain the output of any machine learning model. It connects optimal credit allocation with local explanations using Shapley values from game theory.
                  </p>
                </div>
                <div className="border-l-4 border-blue-400 pl-6">
                  <h4 className="text-lg font-semibold text-[--text] mb-2">How We Use It</h4>
                  <p className="text-sm text-[--muted]">
                    For each event prediction, we calculate SHAP values for all input features (event type, sector, market conditions, historical patterns, etc.). The visualization shows which features pushed the prediction higher or lower.
                  </p>
                </div>
                <div className="border-l-4 border-blue-400 pl-6">
                  <h4 className="text-lg font-semibold text-[--text] mb-2">Multi-Horizon Support</h4>
                  <p className="text-sm text-[--muted]">
                    SHAP explanations are available for all three prediction horizons: 1-day, 7-day, and 30-day. Different features may dominate at different time scales.
                  </p>
                </div>
              </div>
              <div className="rounded-xl border border-white/10 bg-black/20 p-4">
                <h4 className="text-sm font-semibold text-[--text] mb-3">Example Feature Contributions</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-[--muted]">Event Type: FDA Approval</span>
                    <span className="text-green-400 font-mono">+18.5</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[--muted]">Sector: Biotech</span>
                    <span className="text-green-400 font-mono">+12.3</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[--muted]">Market Volatility: High</span>
                    <span className="text-red-400 font-mono">-4.2</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-[--muted]">Historical Pattern Match</span>
                    <span className="text-green-400 font-mono">+8.7</span>
                  </div>
                  <div className="flex items-center justify-between border-t border-white/10 pt-2 mt-2">
                    <span className="text-[--text] font-semibold">Final Prediction Adjustment</span>
                    <span className="text-[--accent] font-mono font-bold">+35.3</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Sector Analysis & Rotation Signals
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8 mb-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary]">
                  <BarChart3 className="h-6 w-6" />
                </div>
                <div>
                  <span className="text-xs font-semibold bg-green-500/20 text-green-400 px-2 py-1 rounded-full">NEW</span>
                  <h3 className="text-xl font-semibold text-[--text] mt-1">Sector-Level Performance Tracking</h3>
                </div>
              </div>
              <p className="text-[--muted] mb-6">
                Our backtesting framework now includes sector-level analysis to identify rotation signals and momentum trends across market sectors.
              </p>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                  <span className="text-[--text]"><strong>Rotation Signals:</strong> Detect capital inflow/outflow between sectors based on event activity and price movements</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                  <span className="text-[--text]"><strong>Momentum Scoring:</strong> Track sector momentum using event-driven price changes over multiple time horizons</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                  <span className="text-[--text]"><strong>Event Clustering:</strong> Identify when multiple high-impact events concentrate in specific sectors</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                  <span className="text-[--text]"><strong>Cross-Sector Correlation:</strong> Discover relationships between sector movements and event types</span>
                </li>
              </ul>
              <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Integration:</span> Sector analysis feeds into the Trade Signal generation, allowing for sector-aware position sizing and risk management across your portfolio.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Data Quality & Transparency
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="space-y-4 text-[--muted]">
                <p>
                  Impact Radar is built on verifiable, traceable data. Events from automated scanners include links to original source documents where available. Price calculations use publicly available market data. All formulas are documented and reproducible.
                </p>
                <p>
                  Our Data Quality Dashboard (available in the app) provides real-time freshness indicators, pipeline health monitoring, and data lineage tracking. You can see exactly when data was last updated, which scanner collected it, and how outcomes were calculated.
                </p>
                <p className="text-[--text] font-semibold">
                  We believe in radical transparency. If you can't verify it, you shouldn't trust it. That's why events include the base deterministic score and, when available, ML-adjusted predictions with links to original source documents.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-6">
              <div className="flex gap-4">
                <Lightbulb className="h-6 w-6 text-yellow-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Research & Educational Tool
                  </h3>
                  <p className="text-sm text-[--muted]">
                    Impact Radar is designed for research and educational purposes. All predictions, scores, and analytics are research tools intended for analysis and learning, not guarantees or investment advice. Always conduct your own due diligence and consult with qualified financial professionals before making investment decisions.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 max-w-4xl mx-auto text-center">
            <p className="text-sm text-[--muted]">
              Full strategy framework | Custom entry/exit rules | Position sizing | Comprehensive metrics (Sharpe, Sortino, CAGR) | Continuous learning since November 2025
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
