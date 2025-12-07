import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function QuickstartPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="mx-auto max-w-4xl px-6 lg:px-8">
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight text-[--text] mb-6">
            Quickstart Guide
          </h1>
          <p className="text-lg text-[--muted] mb-12">
            Get up and running with Impact Radar in minutes.
          </p>

          <div className="space-y-12">
            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                1. Create Your Account
              </h2>
              <p className="text-[--muted] mb-4">
                Sign up for a free account to start tracking market-moving
                events.
              </p>
              <Button asChild>
                <Link href="/app">Sign Up Free</Link>
              </Button>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                2. Build Your Watchlist
              </h2>
              <p className="text-[--muted] mb-4">
                Add companies you're interested in tracking by ticker symbol.
                Your watchlist helps you filter events to see only what matters
                to you.
              </p>
              <div className="rounded-xl bg-[--bg] p-4 font-mono text-sm text-[--text] mt-4">
                Navigate to Watchlist → Add Ticker → Enter symbol (e.g., AAPL)
              </div>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                3. Configure Alerts (Pro)
              </h2>
              <p className="text-[--muted] mb-4">
                Set up email or SMS alerts for specific event types or impact
                score thresholds.
              </p>
              <Button variant="outline" asChild>
                <Link href="/pricing">View Pro Features</Link>
              </Button>
            </section>

            <section className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <h2 className="text-2xl font-semibold text-[--text] mb-6">
                4. Integrate via API (Pro)
              </h2>
              <p className="text-[--muted] mb-4">
                Connect Impact Radar to your own systems using our REST API.
              </p>
              <Button variant="outline" asChild>
                <Link href="/docs/api">API Reference</Link>
              </Button>
            </section>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
