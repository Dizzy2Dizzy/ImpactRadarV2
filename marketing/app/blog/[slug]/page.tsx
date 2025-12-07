import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Calendar, Clock, ArrowLeft, Share2 } from "lucide-react";

const blogPosts: Record<string, any> = {
  "sec-8k-filing-trading-strategy": {
    title: "How to Build a Profitable SEC 8-K Filing Trading Strategy",
    excerpt:
      "Learn how professional traders use SEC 8-K filings to identify market-moving events before the crowd.",
    category: "Trading Strategy",
    date: "2025-11-15",
    readTime: "8 min read",
    author: "Impact Radar Research Team",
    content: `
# Introduction

SEC Form 8-K filings represent some of the most actionable signals in equity markets. These "current reports" are filed when material events occur that shareholders should know about immediately—well before the next quarterly earnings report.

Professional traders have long used 8-K filings as a cornerstone of event-driven strategies. This guide breaks down exactly how to build a profitable approach using Impact Radar's deterministic and ML-enhanced impact scoring.

## What Are 8-K Filings?

SEC Form 8-K is filed by public companies to announce major events including:

- **Corporate changes**: Leadership changes, board appointments
- **Financial events**: Asset acquisitions, debt offerings, bankruptcy
- **Operational updates**: Loss of major customers, contract wins
- **Legal matters**: Material litigation, regulatory proceedings

The SEC requires these filings within 4 business days of the triggering event, creating a tight window for traders to react.

## Why 8-K Filings Matter for Trading

Unlike scheduled earnings announcements, 8-K filings are **unscheduled** and often **unexpected**. This creates several trading advantages:

1. **Information asymmetry**: Most retail traders don't monitor EDGAR filings
2. **Price inefficiency**: Markets may take hours to fully digest the news
3. **Quantifiable impact**: Impact Radar scores each filing 0-100 with directional confidence
4. **Backtestable signals**: Historical filings enable strategy validation

## Building Your 8-K Trading Strategy

### Step 1: Define Your Universe

Start with liquid, tradable stocks where 8-K events actually move prices:

- Market cap: $500M - $50B (sweet spot for volatility)
- Average daily volume: >1M shares
- Sectors: Focus on Tech, Biotech, Finance where events matter most

**Impact Radar tip**: Use the Companies page to filter by sector and market cap, then add qualifying tickers to your watchlist.

### Step 2: Set Up Real-Time Alerts

Speed matters. Configure alerts for high-impact 8-K filings:

- **Impact score**: ≥70 (major events only)
- **Sectors**: Your focus sectors
- **Delivery**: SMS for instant notification during market hours

**Impact Radar tip**: Pro plan users get real-time alerts with zero delay. Free users have a 15-minute delay—insufficient for this strategy.

### Step 3: Score Events Systematically

Not all 8-K items are created equal. Impact Radar's scoring considers:

- **Item type**: Item 2.02 (results) vs Item 5.02 (director departure)
- **Company fundamentals**: Market cap, volatility, recent performance
- **Historical patterns**: How similar events moved this stock before
- **ML enhancement**: Market Echo Engine learns from actual price outcomes

**Example scoring**:
- CEO resignation at $2B tech company: Score 75, Direction: Negative, Confidence: Medium
- Major contract win at $500M defense contractor: Score 85, Direction: Positive, Confidence: High

### Step 4: Execute with Discipline

Develop clear entry/exit rules:

**Entry criteria**:
- Impact score ≥70
- Confidence: Medium or High
- Verify source document (Impact Radar provides direct EDGAR links)
- Check technical setup (avoid counter-trend trades)

**Position sizing**:
- Risk 0.5-1% of capital per signal
- Size inversely to stock volatility
- Increase exposure for High confidence events

**Exit rules**:
- Take profit: +2-3% for positive events, short -2-3% for negative
- Stop loss: -1% (tight risk control)
- Time stop: Close within 1-3 days

### Step 5: Backtest & Refine

Impact Radar's backtesting feature lets you validate your rules against historical data:

1. Navigate to Analytics → Backtesting
2. Filter: Event type = "SEC 8-K", Score ≥70
3. Time period: Last 12 months
4. Analyze: Win rate, average move, optimal holding period

**Key metrics to track**:
- Directional accuracy (aim for 65%+)
- Average absolute price move (2%+ ideal)
- Risk/reward ratio (should exceed 2:1)
- Drawdown periods

## Real-World Example

**Company**: NVDA (NVIDIA)  
**Event**: Item 8.01 - Major AI partnership announcement (8-K filing)  
**Impact Radar Score**: 88 (Positive, High Confidence)  
**Strategy execution**:
- Alert received: 4:15 PM ET (after hours)
- Verified EDGAR source document
- Entered at market open: $485.20
- Stock moved to $497.80 (+2.6%) within 2 days
- Exited at target: +2.5% gain

## Common Pitfalls to Avoid

1. **Chasing every filing**: Focus only on high scores (≥70)
2. **Ignoring liquidity**: Wide spreads kill profits on small-caps
3. **Over-leveraging**: Keep position sizes disciplined
4. **Forgetting fundamentals**: A bullish 8-K can't save a broken company
5. **Not validating sources**: Always verify with EDGAR link

## Advanced Techniques

### Correlation Analysis

Use Impact Radar's correlation engine to find event patterns:
- "CEO departures → Earnings miss" (6-week lag)
- "Acquisition announced → Integration issues" (90-day lag)

### Portfolio Risk

Upload your holdings to check 8-K event exposure:
- How many positions have pending regulatory filings?
- Which sectors have clustered event risk this week?

### API Integration

Pro/Enterprise users can integrate Impact Radar scores into algorithmic systems:
- Real-time WebSocket feed for sub-second latency
- Batch scoring API for portfolio screening
- Historical data API for backtesting

## Conclusion

SEC 8-K filings represent one of the purest forms of event-driven alpha. With Impact Radar's deterministic scoring, ML-enhanced predictions, and comprehensive backtesting tools, individual traders can compete with institutional players.

**Next steps**:
1. Sign up for Impact Radar Pro (7-day free trial)
2. Build your watchlist of qualifying stocks
3. Configure real-time alerts for Score ≥70 events
4. Paper trade for 2-4 weeks to calibrate
5. Go live with tight risk controls

The edge is real—but discipline wins.
    `,
  },
};

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const post = blogPosts[params.slug];

  if (!post) {
    return {
      title: "Post Not Found | Impact Radar",
    };
  }

  return {
    title: `${post.title} | Impact Radar Blog`,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
    },
  };
}

export default function BlogPostPage({ params }: { params: { slug: string } }) {
  const post = blogPosts[params.slug];

  if (!post) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="pt-24 pb-16">
        <article className="max-w-4xl mx-auto px-6 lg:px-8">
          <Link
            href="/blog"
            className="inline-flex items-center gap-2 text-sm text-[--muted] hover:text-[--text] mb-8"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Blog
          </Link>

          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-sm font-medium text-[--primary]">
                {post.category}
              </span>
              <span className="text-sm text-[--muted]">•</span>
              <span className="text-sm text-[--muted] flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                {new Date(post.date).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <span className="text-sm text-[--muted]">•</span>
              <span className="text-sm text-[--muted] flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {post.readTime}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-[--text] mb-4">
              {post.title}
            </h1>

            <p className="text-lg text-[--muted] mb-6">{post.excerpt}</p>

            <div className="flex items-center justify-between py-6 border-y border-white/10">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-gradient-to-br from-[--primary] to-blue-600 flex items-center justify-center text-sm font-semibold text-black">
                  IR
                </div>
                <div>
                  <div className="font-semibold text-[--text]">
                    {post.author}
                  </div>
                  <div className="text-sm text-[--muted]">Research Team</div>
                </div>
              </div>
              <button className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-[--panel] px-4 py-2 text-sm font-medium text-[--text] hover:border-[--primary]/50 transition-colors">
                <Share2 className="h-4 w-4" />
                Share
              </button>
            </div>
          </div>

          <div className="prose prose-invert prose-lg max-w-none">
            <div
              className="text-[--muted] leading-relaxed"
              dangerouslySetInnerHTML={{
                __html: post.content
                  .split("\n")
                  .map((line: string) => {
                    if (line.startsWith("# ")) {
                      return `<h1 class="text-3xl font-bold text-[--text] mt-12 mb-6">${line.slice(2)}</h1>`;
                    }
                    if (line.startsWith("## ")) {
                      return `<h2 class="text-2xl font-bold text-[--text] mt-10 mb-4">${line.slice(3)}</h2>`;
                    }
                    if (line.startsWith("### ")) {
                      return `<h3 class="text-xl font-semibold text-[--text] mt-8 mb-3">${line.slice(4)}</h3>`;
                    }
                    if (line.startsWith("- **")) {
                      const match = line.match(/- \*\*(.+?)\*\*: (.+)/);
                      if (match) {
                        return `<li class="ml-6 mb-2"><strong class="text-[--text]">${match[1]}</strong>: ${match[2]}</li>`;
                      }
                    }
                    if (line.startsWith("- ")) {
                      return `<li class="ml-6 mb-2">${line.slice(2)}</li>`;
                    }
                    if (line.startsWith("**") && line.endsWith("**:")) {
                      return `<p class="font-semibold text-[--text] mt-6 mb-2">${line.slice(2, -3)}:</p>`;
                    }
                    if (line.includes("**")) {
                      return `<p class="mb-4">${line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-[--text]">$1</strong>')}</p>`;
                    }
                    if (line.startsWith("---")) {
                      return '<hr class="my-12 border-white/10" />';
                    }
                    if (line.trim() === "") {
                      return "";
                    }
                    if (line.includes("[") && line.includes("](")) {
                      const match = line.match(/\[(.+?)\]\((.+?)\)/);
                      if (match) {
                        return `<p class="mb-4"><a href="${match[2]}" class="text-[--primary] hover:underline">${match[1]}</a></p>`;
                      }
                    }
                    return `<p class="mb-4">${line}</p>`;
                  })
                  .join(""),
              }}
            />
          </div>

          <div className="mt-16 rounded-2xl border border-white/10 bg-[--panel] p-8">
            <h3 className="text-2xl font-bold text-[--text] mb-4">
              Ready to start trading SEC filings?
            </h3>
            <p className="text-[--muted] mb-6">
              Get real-time 8-K alerts with ML-enhanced impact scores. Start your
              7-day free trial today.
            </p>
            <Link
              href="/signup?plan=pro&trial=7"
              className="inline-flex items-center gap-2 rounded-lg bg-[--primary] px-6 py-3 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
            >
              Start Free Trial
              <ArrowLeft className="h-4 w-4 rotate-180" />
            </Link>
          </div>
        </article>
      </main>
      <Footer />
    </div>
  );
}
