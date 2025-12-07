import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { CodeBlock } from "@/components/docs/CodeBlock";
import Link from "next/link";

export default function APIDocsPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-5xl px-6 lg:px-8">
          <h1 className="text-4xl md:text-5xl font-semibold tracking-tight text-[--text]">
            API Documentation
          </h1>
          <p className="mt-6 text-lg text-[--muted]">
            Programmatic access to Impact Radar event-driven signal engine.
            Available for Pro and Team plans.
          </p>

          {/* Quick Links */}
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/docs"
              target="_blank"
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-[--text] transition-colors"
            >
              Interactive API Docs (Swagger UI)
            </Link>
            <Link
              href="/redoc"
              target="_blank"
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-[--text] transition-colors"
            >
              ReDoc Documentation
            </Link>
            <Link
              href="/api/openapi.json"
              target="_blank"
              className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-[--text] transition-colors"
            >
              Download OpenAPI Spec
            </Link>
          </div>

          <div className="mt-12 space-y-16">
            {/* Overview Section */}
            <section id="overview">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Overview</h2>
              <div className="space-y-4">
                <p className="text-[--muted]">
                  The Impact Radar API provides programmatic access to market events, 
                  impact scoring, portfolio risk analysis, and real-time alerts.
                </p>
                <div className="bg-[--panel] border border-white/10 rounded-xl p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <strong className="text-[--text]">Base URL:</strong>
                      <code className="ml-2 text-[--muted] font-mono">/api</code>
                    </div>
                    <div>
                      <strong className="text-[--text]">Response Format:</strong>
                      <code className="ml-2 text-[--muted] font-mono">JSON</code>
                    </div>
                    <div>
                      <strong className="text-[--text]">Authentication:</strong>
                      <code className="ml-2 text-[--muted] font-mono">X-API-Key header</code>
                    </div>
                    <div>
                      <strong className="text-[--text]">OpenAPI Version:</strong>
                      <code className="ml-2 text-[--muted] font-mono">3.1.0</code>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Getting Started Section */}
            <section id="getting-started">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Getting Started</h2>
              <div className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold text-[--text] mb-3">1. Get Your API Key</h3>
                  <p className="text-[--muted] mb-3">
                    API keys are available for Pro and Team plans. Generate yours from your{" "}
                    <Link href="/account/api-keys" className="text-[--primary] hover:underline">
                      Account Settings
                    </Link>.
                  </p>
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-[--text] mb-3">2. Make Your First Request</h3>
                  <CodeBlock language="bash">
{`curl -H "x-api-key: YOUR_API_KEY" \\
  https://api.impactradar.co/api/events/public`}
                  </CodeBlock>
                </div>
              </div>
            </section>

            {/* Authentication Section */}
            <section id="authentication">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Authentication</h2>
              <div className="space-y-4">
                <p className="text-[--muted]">
                  All authenticated endpoints require an API key passed in the{" "}
                  <code className="px-2 py-1 bg-white/5 rounded text-sm font-mono">x-api-key</code> header.
                </p>
                <div className="bg-[--panel] border border-white/10 rounded-xl p-6">
                  <h4 className="font-semibold text-[--text] mb-3">Example Request:</h4>
                  <CodeBlock language="bash">
{`curl -H "x-api-key: rr_live_1234567890abcdef" \\
  https://api.impactradar.co/api/events/search?ticker=AAPL`}
                  </CodeBlock>
                </div>
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
                  <p className="text-sm text-yellow-200">
                    <strong>Security Note:</strong> Never expose your API keys in client-side code or public repositories.
                    Use environment variables and keep keys secure.
                  </p>
                </div>
              </div>
            </section>

            {/* Rate Limits Section */}
            <section id="rate-limits">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Rate Limits</h2>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-4 text-[--text] font-semibold">Plan</th>
                      <th className="text-left py-3 px-4 text-[--text] font-semibold">Monthly Quota</th>
                      <th className="text-left py-3 px-4 text-[--text] font-semibold">Burst Limit</th>
                      <th className="text-left py-3 px-4 text-[--text] font-semibold">Features</th>
                    </tr>
                  </thead>
                  <tbody className="text-[--muted]">
                    <tr className="border-b border-white/5">
                      <td className="py-3 px-4">Free</td>
                      <td className="py-3 px-4">N/A</td>
                      <td className="py-3 px-4">-</td>
                      <td className="py-3 px-4 text-sm">No API access</td>
                    </tr>
                    <tr className="border-b border-white/5">
                      <td className="py-3 px-4 text-[--primary]">Pro</td>
                      <td className="py-3 px-4">10,000 calls/month</td>
                      <td className="py-3 px-4">100 req/min</td>
                      <td className="py-3 px-4 text-sm">Events, scoring, portfolio (3 tickers)</td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 text-[--primary]">Team</td>
                      <td className="py-3 px-4">100,000 calls/month</td>
                      <td className="py-3 px-4">500 req/min</td>
                      <td className="py-3 px-4 text-sm">All features, unlimited tickers</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            {/* Endpoints Section */}
            <section id="endpoints">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Key Endpoints</h2>
              
              {/* GET /events/public */}
              <div className="mb-12 border-l-4 border-[--primary] pl-6">
                <h3 className="text-2xl font-semibold text-[--text] mb-2">
                  <span className="text-green-400 font-mono text-lg">GET</span> /api/events/public
                </h3>
                <p className="text-[--muted] mb-4">
                  Retrieve public event feed with optional filters. No authentication required.
                </p>
                
                <h4 className="font-semibold text-[--text] mt-6 mb-3">Query Parameters:</h4>
                <div className="bg-[--panel] border border-white/10 rounded-lg p-4 space-y-2 text-sm">
                  <div><code className="text-[--primary]">ticker</code> <span className="text-[--muted]">- Filter by ticker symbol (e.g., AAPL)</span></div>
                  <div><code className="text-[--primary]">sector</code> <span className="text-[--muted]">- Filter by sector</span></div>
                  <div><code className="text-[--primary]">min_score</code> <span className="text-[--muted]">- Minimum impact score (0-100)</span></div>
                  <div><code className="text-[--primary]">from_date</code> <span className="text-[--muted]">- Start date (ISO 8601)</span></div>
                  <div><code className="text-[--primary]">to_date</code> <span className="text-[--muted]">- End date (ISO 8601)</span></div>
                  <div><code className="text-[--primary]">limit</code> <span className="text-[--muted]">- Results per page (default: 100)</span></div>
                </div>

                <h4 className="font-semibold text-[--text] mt-6 mb-3">Example:</h4>
                <CodeBlock language="bash">
{`curl "https://api.impactradar.co/api/events/public?ticker=AAPL&min_score=70"`}
                </CodeBlock>
              </div>

              {/* GET /events/search */}
              <div className="mb-12 border-l-4 border-[--primary] pl-6">
                <h3 className="text-2xl font-semibold text-[--text] mb-2">
                  <span className="text-green-400 font-mono text-lg">GET</span> /api/events/search
                  <span className="ml-3 px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded">Pro/Team</span>
                </h3>
                <p className="text-[--muted] mb-4">
                  Advanced event search with full filtering and historical data access. Requires API key.
                </p>

                <h4 className="font-semibold text-[--text] mt-6 mb-3">Example:</h4>
                <CodeBlock language="bash">
{`curl -H "x-api-key: YOUR_API_KEY" \\
  "https://api.impactradar.co/api/events/search?ticker=AAPL&category=earnings"`}
                </CodeBlock>
              </div>

              {/* POST /portfolio/upload */}
              <div className="mb-12 border-l-4 border-blue-500 pl-6">
                <h3 className="text-2xl font-semibold text-[--text] mb-2">
                  <span className="text-blue-400 font-mono text-lg">POST</span> /api/portfolio/upload
                  <span className="ml-3 px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded">Pro/Team</span>
                </h3>
                <p className="text-[--muted] mb-4">
                  Upload portfolio positions from CSV file. Pro plan limited to 3 tickers, Team unlimited.
                </p>

                <h4 className="font-semibold text-[--text] mt-6 mb-3">CSV Format:</h4>
                <CodeBlock language="csv" filename="portfolio.csv">
{`ticker,qty,avg_price,label
AAPL,100,150.50,Core Holdings
MSFT,50,300.00,Tech Growth
TSLA,25,200.00,High Risk`}
                </CodeBlock>
              </div>

              {/* GET /portfolio/insights */}
              <div className="mb-12 border-l-4 border-[--primary] pl-6">
                <h3 className="text-2xl font-semibold text-[--text] mb-2">
                  <span className="text-green-400 font-mono text-lg">GET</span> /api/portfolio/insights
                  <span className="ml-3 px-2 py-1 bg-yellow-500/20 text-yellow-300 text-xs rounded">Pro/Team</span>
                </h3>
                <p className="text-[--muted] mb-4">
                  Analyze portfolio exposure to upcoming events. Returns risk scores and expected dollar moves.
                </p>

                <h4 className="font-semibold text-[--text] mt-6 mb-3">Example:</h4>
                <CodeBlock language="python">
{`import requests

response = requests.get(
    "https://api.impactradar.co/api/portfolio/insights?window_days=14",
    headers={"x-api-key": "YOUR_API_KEY"}
)

insights = response.json()
for position in insights:
    print(f"{position['ticker']}: {position['upcoming_events_count']} events")
    print(f"  Expected 1-day move: \${position['exposure_1d']:.2f}")
    print(f"  Risk score: {position['total_risk_score']:.1f}/100")`}
                </CodeBlock>
              </div>

              {/* GET /companies */}
              <div className="mb-12 border-l-4 border-[--primary] pl-6">
                <h3 className="text-2xl font-semibold text-[--text] mb-2">
                  <span className="text-green-400 font-mono text-lg">GET</span> /api/companies
                </h3>
                <p className="text-[--muted] mb-4">
                  Get list of tracked companies with event counts. Public endpoint.
                </p>

                <h4 className="font-semibold text-[--text] mt-6 mb-3">Example:</h4>
                <CodeBlock language="bash">
{`curl "https://api.impactradar.co/api/companies?sector=Technology&limit=10"`}
                </CodeBlock>
              </div>
            </section>

            {/* Error Handling Section */}
            <section id="errors">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Error Handling</h2>
              <div className="space-y-6">
                <p className="text-[--muted]">
                  All errors return a consistent JSON format with error code, message, and optional details.
                </p>
                
                <div>
                  <h4 className="font-semibold text-[--text] mb-3">Error Response Format:</h4>
                  <CodeBlock language="json">
{`{
  "error_code": "QUOTA_EXCEEDED",
  "message": "API quota exceeded. Upgrade your plan or wait for monthly reset.",
  "details": {
    "quota_limit": 10000,
    "quota_used": 10000,
    "reset_date": "2024-02-01T00:00:00Z"
  },
  "status_code": 402
}`}
                  </CodeBlock>
                </div>

                <div>
                  <h4 className="font-semibold text-[--text] mb-4">Common Error Codes:</h4>
                  <div className="space-y-3">
                    <div className="bg-[--panel] border border-white/10 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <code className="px-2 py-1 bg-red-500/20 text-red-300 rounded text-sm font-mono">401</code>
                        <div>
                          <p className="font-semibold text-[--text]">UNAUTHORIZED</p>
                          <p className="text-sm text-[--muted]">Invalid or missing API key</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-[--panel] border border-white/10 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <code className="px-2 py-1 bg-red-500/20 text-red-300 rounded text-sm font-mono">402</code>
                        <div>
                          <p className="font-semibold text-[--text]">QUOTA_EXCEEDED</p>
                          <p className="text-sm text-[--muted]">Monthly API quota limit reached</p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="bg-[--panel] border border-white/10 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <code className="px-2 py-1 bg-yellow-500/20 text-yellow-300 rounded text-sm font-mono">429</code>
                        <div>
                          <p className="font-semibold text-[--text]">RATE_LIMIT_EXCEEDED</p>
                          <p className="text-sm text-[--muted]">Too many requests, slow down</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Support Section */}
            <section id="support">
              <h2 className="text-3xl font-semibold text-[--text] mb-6">Need Help?</h2>
              <div className="bg-[--panel] border border-white/10 rounded-xl p-8">
                <p className="text-[--muted] mb-6">
                  Check out our interactive API documentation or contact support if you have questions.
                </p>
                <div className="flex flex-wrap gap-4">
                  <Link
                    href="/pricing"
                    className="px-6 py-3 bg-[--primary] hover:bg-[--primary]/90 text-white rounded-lg font-medium transition-colors"
                  >
                    Upgrade Your Plan
                  </Link>
                  <Link
                    href="/contact"
                    className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-[--text] rounded-lg font-medium transition-colors"
                  >
                    Contact Support
                  </Link>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
