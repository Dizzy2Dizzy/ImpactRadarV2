# Market Echo Engine - Limitations & Constraints

**Last Updated:** November 20, 2025  
**Status:** Experimental Prototype  
**Purpose:** Transparency document for users and stakeholders

---

## Overview

The Market Echo Engine is an experimental, self-learning ML system that improves event impact predictions by learning from realized stock price movements. While showing promising early results (71.3% directional accuracy on 1-day predictions), it is important to understand its current limitations and constraints.

---

## Current Status: Prototype

### ⚠️ Limited Training Data

**Current Dataset (as of Nov 20, 2025):**
- **355 labeled SEC 8-K events** (only 2 days of labeled data)
- **238 unique companies**
- **Primarily one event family** (SEC 8-K filings)
- **Limited coverage** of FDA approvals, earnings, M&A, and other event types

**What This Means:**
- Predictions are statistically promising but **not yet robust**
- Model may not generalize well to unseen companies or event types
- Need 1,000-1,500+ labeled events for statistical confidence
- Other event families (FDA, earnings) are in very early stages

---

## Key Limitations

### 1. Non-Stationarity of Markets

**The Challenge:**
- Financial markets are non-stationary (patterns change over time)
- What worked last quarter may not work next quarter
- Market regimes shift due to policy changes, economic cycles, sentiment

**Our Safeguards:**
- Daily automated retraining to adapt to recent patterns
- Drift detection monitors model performance degradation
- Models automatically retrain when accuracy drops >2%

**Reality Check:**
Even with continuous learning, the market can surprise us. Past patterns are not guarantees of future performance.

---

### 2. Regime Shift Risk

**The Challenge:**
- Major market events (crashes, rallies, policy changes) can invalidate learned patterns
- Black swan events are by definition unpredictable
- Model trained on normal conditions may fail during crises

**Our Safeguards:**
- ±20 point maximum ML adjustment (prevents wild swings)
- Confidence-weighted blending (low confidence = stick to deterministic base)
- Continuous monitoring of accuracy degradation

**Reality Check:**
The system is designed to improve calibration in normal markets, not predict black swans.

---

### 3. Limited Sample Sizes

**Current Sample Sizes:**
- **SEC 8-K family:** 355 events ✅ (prototype-ready)
- **FDA approvals:** <50 events ⚠️ (insufficient for ML)
- **Earnings:** <30 events ⚠️ (insufficient for ML)
- **M&A:** <20 events ⚠️ (insufficient for ML)

**Production Thresholds:**
- Minimum for family-specific model: **100 events + 20 unique companies**
- Minimum for prototype: **30 events + 10 unique companies**

**What This Means:**
- Only SEC 8-K has a dedicated ML model (as of Nov 20, 2025)
- Other families fall back to global model or deterministic-only
- Predictions for non-SEC events are less reliable

---

### 4. Company-Specific Patterns

**The Challenge:**
- Each company is unique (business model, investor expectations, sector dynamics)
- Small-cap vs large-cap stocks behave differently
- Biotech reactions differ from tech reactions

**Our Approach:**
- Learn company-specific patterns where data exists
- Use EventStats to track historical behavior per ticker
- Family-specific models capture sector-level patterns

**Reality Check:**
With only 238 companies in training data, company-specific predictions are limited. Generic patterns dominate.

---

### 5. Abnormal Returns Are Noisy

**The Methodology:**
We measure **abnormal returns** (stock return minus SPY benchmark):
```
abnormal_return = stock_return - SPY_return
```

This removes general market noise, but:
- **Sector-specific moves** are not removed (e.g., entire biotech sector rallies)
- **Idiosyncratic noise** remains (random day-to-day volatility)
- **Event timing** matters (price may move before/after the official event)

**What This Means:**
Even "correct" predictions may show magnitude errors due to noise. A score of 70 doesn't mean exactly 7% move - it's a relative severity estimate.

---

## Guardrails & Safety Mechanisms

### 1. Limited ML Adjustment Range

**Rule:** ML can only adjust impact_score by **±20 points maximum**

**Why:**
- Prevents wild, unpredictable swings
- Keeps predictions anchored to deterministic base
- Ensures ML acts as "fine-tuning" not "complete override"

**Example:**
- Base score: 50 (neutral)
- ML predicts: -30% return (very negative)
- Final score: 50 → 30 (maximum -20 point adjustment)

---

### 2. Confidence-Weighted Blending

**Formula:**
```
ml_delta = (ml_prediction - base_score) * ml_confidence
final_score = base_score + clamp(ml_delta, -20, +20)
```

**Why:**
- Low confidence predictions stick closer to base score
- High confidence predictions get more adjustment weight
- Prevents overconfident predictions from dominating

---

### 3. No Buy/Sell/Hold Signals

**What We Do NOT Do:**
- Provide trading recommendations
- Suggest specific actions (buy, sell, hold)
- Offer investment advice

**What We DO Do:**
- Provide **impact estimates** (how significant the event is)
- Offer **directional signals** (bullish, bearish, neutral)
- Share **data and rationale** for transparency

**Legal Disclaimer:**
Impact Radar is a research and analysis tool. It is **NOT investment advice**. All trading decisions are your responsibility.

---

## Data Freshness & Staleness

### Labeling Lag

**Process:**
1. Event occurs on Day 0
2. We wait T+1, T+5, T+20 days for price data
3. Label gets created after price stabilizes
4. Model retrains when 50+ new labels or 7+ days elapsed

**What This Means:**
- **1-day labels:** Available 3 days after event (allows for weekend buffer)
- **5-day labels:** Available 10 days after event
- **20-day labels:** Available 30 days after event

**Implication:**
Recent events don't contribute to ML training immediately. There's a natural lag between event occurrence and model learning.

---

### Model Retraining Frequency

**Current Schedule:**
- **Daily check** for retraining triggers
- **Retrain when:**
  - 50+ new labeled samples available
  - 7+ days since last training
  - Accuracy drops >2% from baseline

**What This Means:**
- Models stay fresh (not using stale year-old patterns)
- Not overly reactive (doesn't retrain on every single event)
- Balances adaptation with stability

---

## Transparency & Explainability

### What You See

**For Every Prediction:**
1. **Base Score** (deterministic rules) - Always visible
2. **ML-Adjusted Score** (with Market Echo) - Shown when ML applied
3. **ML Confidence** (0.0-1.0) - How certain the model is
4. **Model Source** - "family-specific", "global", or "deterministic-only"
5. **Model Version** - e.g., "v1.0.2"
6. **Horizon** - Which time window (1d, 5d, 20d)

**Why This Matters:**
- You can see **exactly** how ML influenced the score
- You can judge **confidence** levels yourself
- You can toggle AI adjustments on/off (future feature)

---

## What We're NOT Claiming

❌ **We are NOT claiming:**
- Perfect predictions or guaranteed accuracy
- Ability to predict black swan events
- Statistical significance with current sample sizes
- Production-grade reliability for all event types

✅ **We ARE claiming:**
- Honest, transparent prototyping approach
- 71.3% directional accuracy on current SEC 8-K dataset
- Continuous learning and improvement as data grows
- Clear guardrails and safety mechanisms

---

## Future Improvements

### Short-Term (1-2 Months)

**Goal:** Scale to 1,000-1,500 labeled events
- Expand SEC 8-K coverage (more companies, more time)
- Add FDA approval labeling pipeline
- Add earnings event labeling
- Improve company diversity (currently 238 → target 500+)

**Expected Outcome:**
- 75-80% directional accuracy (up from 71.3%)
- Family-specific models for FDA and earnings
- More robust company-specific patterns

---

### Medium-Term (3-6 Months)

**Goal:** Multi-horizon predictions
- Currently models predict separately for 1d, 5d, 20d
- Future: Unified model predicting all horizons together
- Better understanding of event impact timing

**Goal:** Feature engineering improvements
- Add sentiment analysis from event text
- Include market regime indicators
- Incorporate sector-specific volatility measures

---

### Long-Term (6-12 Months)

**Goal:** Production-ready status
- 2,000+ labeled events across all families
- Statistically significant validation sets
- Published backtesting reports with confidence intervals
- A/B testing of model versions

**Goal:** Advanced features
- User-adjustable ML confidence thresholds
- Toggle AI adjustments on/off per preference
- Custom scoring weights based on user strategy

---

## How to Use This System Responsibly

### ✅ DO Use For:
1. **Initial screening** - Prioritize which events to research deeper
2. **Directional signals** - Get a sense of bullish/bearish/neutral bias
3. **Impact severity** - Understand relative significance of events
4. **Pattern learning** - See which event types historically move prices
5. **Research tool** - Combine with your own analysis

### ❌ DO NOT Use For:
1. **Sole trading decision** - Always combine with other analysis
2. **High-frequency trading** - Lag time makes this unsuitable
3. **Guaranteed profits** - No system can guarantee market returns
4. **Black swan prediction** - System cannot predict unprecedented events
5. **Legal/investment advice** - This is a research tool only

---

## Contact & Feedback

**Questions about limitations?**
- Review our [Technical Documentation](./ML_ARCH_NOTES.md)
- Visit the [Market Echo Engine page](/market-echo) for methodology

**Found an issue or have feedback?**
- We value transparency and continuous improvement
- Help us identify edge cases and failure modes
- Your feedback makes the system better for everyone

---

## Legal Disclaimer

**IMPORTANT: Not Investment Advice**

Impact Radar and the Market Echo Engine are provided for **informational and research purposes only**. They do not constitute investment advice, financial advice, trading advice, or any other sort of advice.

**You are solely responsible** for determining whether any investment, security, or strategy is appropriate for you based on your investment objectives, financial situation, and risk tolerance.

**Past performance is not indicative of future results.** The ML models are trained on historical data, which may not predict future market behavior.

**Use at your own risk.** The creators of Impact Radar shall not be liable for any losses or damages arising from the use of this system.

---

**Remember:** The Market Echo Engine is a prototype designed to improve over time. As it learns from more data, predictions should become more calibrated. But it will never be perfect - markets are inherently unpredictable.

**Our commitment:** Radical transparency about what works, what doesn't, and what we're learning along the way.
