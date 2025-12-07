"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Rocket, ArrowRight, CheckCircle2 } from "lucide-react";

export default function AppPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.error || "Failed to subscribe");
        setLoading(false);
        return;
      }

      setSuccess(true);
      setEmail("");
      setLoading(false);
    } catch (err) {
      setError("An error occurred. Please try again.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center px-6 py-24">
        <div className="text-center max-w-3xl">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-[--primary]/20 to-[--accent]/20 text-[--primary] mb-8">
            <Rocket className="h-10 w-10" />
          </div>
          <h1 className="text-4xl md:text-6xl font-semibold text-[--text] mb-6">
            Welcome to <span className="text-[--primary]">Impact Radar</span>
          </h1>
          <p className="text-lg text-[--muted] mb-12 max-w-2xl mx-auto">
            Track market-moving events, FDA announcements, SEC filings, and earnings in real-time with deterministic impact scoring.
          </p>
          <div className="flex gap-4 justify-center flex-wrap mb-12">
            <Button size="lg" asChild>
              <Link href="/signup">
                Get Started <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/product">Explore Features</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/pricing">View Pricing</Link>
            </Button>
          </div>
          <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
            <h2 className="text-xl font-semibold text-[--text] mb-4">
              Stay Updated
            </h2>
            <p className="text-[--muted] mb-6">
              Subscribe to receive important updates, new features, and market alerts from Impact Radar.
            </p>
            
            {success ? (
              <div className="flex items-center justify-center gap-3 py-4 text-green-400">
                <CheckCircle2 className="h-5 w-5" />
                <span>Successfully subscribed!</span>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="max-w-md mx-auto">
                {error && (
                  <div className="mb-4 text-sm text-red-400 text-center">
                    {error}
                  </div>
                )}
                <div className="flex gap-3">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="flex-1 rounded-lg border border-white/10 bg-[--bg] px-4 py-3 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                    aria-label="Email address"
                  />
                  <Button type="submit" disabled={loading}>
                    {loading ? "Subscribing..." : "Subscribe"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
