import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Brain, TrendingUp, Target, Zap, Activity, CheckCircle2, BarChart3, Shield, Lightbulb, AlertTriangle, Layers, MessageCircle, Award, Network, Gauge, GitBranch } from "lucide-react";

const echoPhases = [
  {
    icon: <Target className="h-6 w-6" />,
    phase: "Phase 1",
    title: "Make Prediction",
    description:
      "When a major event happens (earnings, FDA approval, merger), our system calculates an impact score (0-100) predicting how much it will move the stock price.",
  },
  {
    icon: <Activity className="h-6 w-6" />,
    phase: "Phase 2",
    title: "Market Echoes Back",
    description:
      "The market responds over the next 1, 5, and 20 days. Did the stock actually move as predicted? The market \"echoes back\" the answer through real price movements.",
  },
  {
    icon: <Brain className="h-6 w-6" />,
    phase: "Phase 3",
    title: "Learn from Reality",
    description:
      "Our AI compares predictions to what actually happened. It learns which event types, companies, and market conditions lead to bigger or smaller price moves.",
  },
  {
    icon: <TrendingUp className="h-6 w-6" />,
    phase: "Phase 4",
    title: "Improve Predictions",
    description:
      "The next time a similar event occurs, the AI adjusts the impact score based on what it learned. Predictions are designed to improve calibration over time.",
  },
];

const keyFeatures = [
  {
    icon: <BarChart3 className="h-6 w-6" />,
    title: "Abnormal Returns",
    description:
      "We measure event impact by removing general market noise. If the S&P 500 went up 2% and the stock went up 8%, the true event impact is +6%.",
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: "AI Guardrails",
    description:
      "The AI can only nudge scores by ±20 points, weighted by confidence. Low-confidence predictions stick close to the base score. You stay in control.",
  },
  {
    icon: <Lightbulb className="h-6 w-6" />,
    title: "Full Transparency",
    description:
      "Every prediction shows you three numbers: the base score (deterministic rules), the AI's raw prediction (ML model), and the final blended result (confidence-weighted). You can toggle AI adjustments on/off at any time. No black boxes.",
  },
];

const learningMetrics = [
  "Dual-model ensemble: XGBoost gradient boosting and PyTorch neural network with dynamic weighting",
  "Hierarchical model architecture: event-type-specific models when sufficient data exists, global models as intelligent fallback",
  "Seven event type families: SEC filings, earnings, FDA approvals, M&A, guidance updates, dividends, analyst ratings",
  "2,670+ events validated with verified price outcomes across 890+ tickers",
  "Three time horizons: 1-day (66% accuracy), 5-day (59% accuracy), and 20-day predictions",
  "55+ engineered features: volatility, sector trends, market regime, event history, technical indicators, and topology context",
  "Neural network with gated attention mechanism and confidence calibration (Platt scaling)",
  "Online learning capability for incremental model updates from new market data",
  "Twitter/X sentiment integration for real-time social signal analysis (Coming Soon)",
  "Topology-based market analysis with correlation clustering and regime detection",
  "Daily retraining pipeline with automatic model versioning and performance tracking",
];

const technicalHighlights = [
  {
    metric: "66%",
    label: "1-Day Win Rate",
    description: "Direction accuracy for 1-day predictions across 2,670+ verified event outcomes",
  },
  {
    metric: "59%",
    label: "5-Day Accuracy",
    description: "Directional accuracy for 5-day predictions across verified event outcomes",
  },
  {
    metric: "2,670+",
    label: "Verified Outcomes",
    description: "Events with confirmed price movements used to train and validate the models",
  },
  {
    metric: "890+",
    label: "Tickers Covered",
    description: "Unique companies with validated prediction outcomes for training data",
  },
];

const ensembleFeatures = [
  {
    icon: <Layers className="h-6 w-6" />,
    title: "Neural Network Ensemble",
    description:
      "PyTorch-based neural network works alongside XGBoost with dynamic weighting. Both models run in parallel, and their predictions are blended based on rolling 30-day accuracy scores.",
  },
  {
    icon: <Award className="h-6 w-6" />,
    title: "Confidence Calibration",
    description:
      "Platt scaling and isotonic regression ensure probability estimates are well-calibrated. When the model says 70% confidence, it's right approximately 70% of the time.",
  },
  {
    icon: <TrendingUp className="h-6 w-6" />,
    title: "Online Learning",
    description:
      "The neural network continuously learns from new market data with incremental updates. As new events resolve, the model adapts using reduced learning rates for stability.",
  },
];

const sentimentFeatures = [
  "Real-time Twitter/X sentiment analysis for market events and tickers",
  "Financial-optimized sentiment scoring trained on market language patterns",
  "Volume tracking and engagement metrics for social signal strength",
  "Bullish/bearish/neutral classification with confidence scores",
  "7-day historical sentiment trends for event context",
  "Demo mode available for testing without API credentials",
];

const topologyFeatures = [
  {
    icon: <Network className="h-6 w-6" />,
    title: "Correlation Clustering",
    description:
      "Stocks are dynamically grouped into clusters based on price correlation patterns. Events affecting one stock in a cluster often impact related stocks, improving prediction context.",
  },
  {
    icon: <Gauge className="h-6 w-6" />,
    title: "Market Regime Detection",
    description:
      "Real-time classification of market conditions as RISK-ON or RISK-OFF. During risk-off periods, bullish events may have dampened impact while bearish events amplify.",
  },
  {
    icon: <GitBranch className="h-6 w-6" />,
    title: "Cluster Context",
    description:
      "Each event prediction now considers cluster-level volatility and recent returns. High-volatility clusters signal more uncertain outcomes.",
  },
];

const topologyMetrics = [
  "7 meaningful market clusters with 66.6% average sector purity",
  "Energy sector achieves 100% cluster purity for precise predictions",
  "+5.8% accuracy improvement in event predictions with topology features",
  "Real-time regime detection with confidence scoring (RISK-ON/RISK-OFF)",
  "Cluster-level volatility and 5-day return tracking for context",
  "Dynamic breadth measurement for market health assessment",
];

export default function MarketEchoPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text]">
              Market Echo <span className="text-[--primary]">Engine</span>
            </h1>
            <p className="mt-6 text-lg text-[--muted]">
              Our self-learning AI system that is designed to improve event impact predictions by learning from real market outcomes. The market echoes back whether we were right, and the AI adapts over time.
            </p>
          </div>

          <div className="mt-16 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-6">
              <div className="flex gap-4">
                <Lightbulb className="h-6 w-6 text-yellow-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    What Market Echo Is (and Isn't)
                  </h3>
                  <p className="text-sm text-[--muted] mb-2">
                    Market Echo is an experimental AI layer that adjusts impact scores based on how similar events have actually moved prices in the past. It does not execute trades or guarantee outcomes, and it never replaces the underlying event data.
                  </p>
                  <p className="text-sm text-[--muted]">
                    You always see both the base impact score and the AI-adjusted score. You can toggle AI adjustments on or off in your settings. The AI can only nudge scores within a limited range (±20 points max) based on its confidence level.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-8 max-w-4xl mx-auto">
            <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-6">
              <div className="flex gap-4">
                <Zap className="h-6 w-6 text-blue-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    How It Works: The Echo Metaphor
                  </h3>
                  <p className="text-sm text-[--muted]">
                    Think of every market event as a sound wave. We make a prediction (the initial wave), the market responds with actual price movements (the echo), and our AI learns from comparing the two. Over time, our predictions are designed to improve calibration because we learn from thousands of market echoes.
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
                    Prototype Status
                  </h3>
                  <p className="text-sm text-[--muted] mb-2">
                    <strong>Current Training Data:</strong> The Market Echo Engine has been trained on <strong>2,670+ events</strong> with verified price outcomes across 890+ tickers and is continuously growing as more events resolve and price data becomes available.
                  </p>
                  <p className="text-sm text-[--muted] mb-2">
                    <strong>Other Event Families:</strong> Additional event type families (earnings, FDA approvals, M&A, guidance updates, dividends, and analyst ratings) are in early labeling stages. As these datasets mature, specialized models will be trained and deployed.
                  </p>
                  <p className="text-sm text-orange-300/90">
                    <strong>Important:</strong> The Market Echo Engine is an experimental research prototype. All predictions and metrics are research tools designed for analysis and learning, not guarantees or investment advice. Always conduct your own due diligence and consult with qualified financial professionals before making investment decisions.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {echoPhases.map((phase) => (
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
              Key Features
            </h2>
            <div className="grid gap-6 md:grid-cols-3">
              {keyFeatures.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-2xl border border-white/10 bg-[--panel] p-6"
                >
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[--primary]/10 text-[--primary] mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-[--muted]">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Intelligent Model Selection
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <p className="text-[--muted] mb-6">
                The Market Echo Engine uses a hierarchical approach to choose the best model for each prediction. This ensures you always get the most accurate, data-driven prediction available.
              </p>
              <div className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500/10 text-green-400 flex items-center justify-center font-semibold text-sm">
                    1
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] mb-1">
                      Event-Type-Specific Models
                    </h3>
                    <p className="text-sm text-[--muted]">
                      When enough similar events exist (150+ samples from 75+ companies), the system trains specialized models for that event family. Currently available for SEC 8-K filings with 1-day and 5-day predictions.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/10 text-blue-400 flex items-center justify-center font-semibold text-sm">
                    2
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] mb-1">
                      Global Fallback Models
                    </h3>
                    <p className="text-sm text-[--muted]">
                      For event types without enough data for specialized models (currently: earnings, FDA approvals, M&A, guidance updates, dividends, analyst ratings), the system uses global models trained across all event families. These provide ML-enhanced predictions while learning patterns across different event types.
                    </p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center font-semibold text-sm">
                    3
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] mb-1">
                      Deterministic Baseline
                    </h3>
                    <p className="text-sm text-[--muted]">
                      If ML predictions are unavailable or have low confidence, the system falls back to rule-based scoring. This ensures predictions never fail and maintain quality standards.
                    </p>
                  </div>
                </div>
              </div>
              <div className="mt-6 rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Model Coverage Transparency:</span> The Backtesting tab shows exactly which event types have specialized models, which use global fallbacks, and training progress for each family. You always know which model is making your predictions.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Performance Metrics
            </h2>
            <div className="rounded-2xl border border-green-500/20 bg-green-500/5 p-6 mb-8">
              <div className="flex gap-4">
                <Award className="h-6 w-6 text-green-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Verified Accuracy Metrics
                  </h3>
                  <p className="text-sm text-[--muted] mb-2">
                    These metrics are calculated from <strong>2,670+ verified event outcomes</strong> with confirmed stock price movements across 890+ tickers.
                  </p>
                  <p className="text-sm text-[--muted]">
                    Our 1-day predictions achieve <strong>66% directional accuracy</strong>, significantly above random chance (50%). The model performs best on short-term horizons where event impact is most immediate.
                  </p>
                </div>
              </div>
            </div>
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
              Neural Network Ensemble
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8 mb-8">
              <p className="text-[--muted] mb-6">
                The Market Echo Engine now uses a dual-model ensemble combining XGBoost gradient boosting with a PyTorch neural network. Both models run predictions in parallel, and their outputs are dynamically weighted based on recent performance.
              </p>
              <div className="grid gap-6 md:grid-cols-3">
                {ensembleFeatures.map((feature) => (
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
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
              <p className="text-sm text-[--muted]">
                <span className="font-semibold text-[--text]">Dynamic Weighting:</span> The ensemble uses a softmax-weighted blend with a minimum 10% weight per model. Each model's weight is determined by its rolling 30-day accuracy, ensuring the best-performing model has the strongest influence while preventing over-reliance on any single approach.
              </p>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Topology-Based Market Analysis
            </h2>
            <div className="rounded-2xl border border-purple-500/20 bg-purple-500/5 p-6 mb-8">
              <div className="flex gap-4">
                <Network className="h-6 w-6 text-purple-400 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Understanding Market Structure
                  </h3>
                  <p className="text-sm text-[--muted]">
                    The Market Echo Engine now analyzes the topological structure of the market using correlation clustering and regime detection. This provides crucial context for predictions: events hitting stocks in high-volatility clusters behave differently than those in stable sectors.
                  </p>
                </div>
              </div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8 mb-8">
              <div className="grid gap-6 md:grid-cols-3">
                {topologyFeatures.map((feature) => (
                  <div
                    key={feature.title}
                    className="rounded-xl border border-white/5 bg-white/5 p-4"
                  >
                    <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-purple-500/10 text-purple-400 mb-3">
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
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h3 className="text-lg font-semibold text-[--text] mb-4">
                Topology Metrics
              </h3>
              <ul className="space-y-3">
                {topologyMetrics.map((metric) => (
                  <li key={metric} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-purple-400 mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{metric}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Dashboard Integration:</span> The current market regime (RISK-ON or RISK-OFF) is displayed on your dashboard overview, helping you understand the broader market context for any event predictions you're analyzing.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Social Sentiment Integration
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="flex items-center gap-3 mb-6">
                <MessageCircle className="h-6 w-6 text-[--primary]" />
                <h3 className="text-lg font-semibold text-[--text]">
                  Twitter/X Real-Time Sentiment
                </h3>
              </div>
              <p className="text-[--muted] mb-6">
                The Market Echo Engine now incorporates social sentiment signals from Twitter/X to provide additional context for event predictions. This helps identify market sentiment shifts that may amplify or dampen event impact.
              </p>
              <ul className="space-y-3">
                {sentimentFeatures.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{feature}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-6 rounded-xl border border-yellow-500/20 bg-yellow-500/5 p-4">
                <p className="text-sm text-[--muted]">
                  <span className="font-semibold text-[--text]">Note:</span> Twitter sentiment requires a valid API bearer token. When credentials are not available, the system operates in demo mode with simulated sentiment data for testing purposes.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Learning Pipeline
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <ul className="space-y-4">
                {learningMetrics.map((metric) => (
                  <li key={metric} className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-[--accent] mt-0.5 flex-shrink-0" />
                    <span className="text-[--text]">{metric}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Real Example
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Day 1: FDA Approval Event
                  </h3>
                  <p className="text-[--muted]">
                    Biotech company XYZ gets FDA approval for a new drug. Our base scoring system predicts impact score of 68 based on historical FDA approvals.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Day 2-20: Market Response
                  </h3>
                  <p className="text-[--muted]">
                    The stock surges 15% in 1 day, 22% in 5 days. The S&P 500 was up 1% during this period, so the abnormal return (event-specific impact) was +21%. This is stronger than our base prediction suggested.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[--text] mb-2">
                    Day 21+: AI Learning
                  </h3>
                  <p className="text-[--muted]">
                    The AI learns that FDA approvals for small-cap biotech in this therapeutic area tend to outperform the base model. Next time a similar event happens, the AI will nudge the score higher (e.g., from 68 to 78) with high confidence.
                  </p>
                </div>
                <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-green-400 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-[--text] mb-1">
                        Result: Calibration Improvement
                      </p>
                      <p className="text-sm text-[--muted]">
                        The system identifies this pattern and is designed to make more calibrated predictions for similar future events. This learning process happens automatically every day across hundreds of labeled events spanning multiple event types.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-24 max-w-4xl mx-auto">
            <h2 className="text-3xl font-semibold text-[--text] mb-8">
              Why This Matters
            </h2>
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="space-y-4 text-[--muted]">
                <p>
                  Traditional event scoring systems are static. They use the same rules forever, regardless of whether they were right or wrong. Our Market Echo Engine is different.
                </p>
                <p>
                  Every single day, the system learns from real market outcomes. When FDA approvals consistently move stocks more than expected, we adjust. When earnings beats in certain sectors have less impact than predicted, we adapt. When market volatility changes how events affect prices, we evolve.
                </p>
                <p className="text-[--text] font-semibold">
                  The result: predictions designed to improve calibration over time, powered by machine learning that helps highlight where the base model tends to over- or under-estimate impact.
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
                    Available on Pro and Enterprise Plans
                  </h3>
                  <p className="text-sm text-[--muted]">
                    ML-enhanced impact scores are available to Pro and Enterprise subscribers. Free and Basic plans use our proven deterministic scoring system.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-12 max-w-4xl mx-auto text-center">
            <p className="text-sm text-[--muted]">
              Neural network ensemble active since November 2025 | 64.6% 1-day accuracy | 1,490+ verified outcomes across 440+ tickers | Topology-based market analysis | Twitter sentiment integration
            </p>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
