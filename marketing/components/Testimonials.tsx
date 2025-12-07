"use client";

import { Star } from "lucide-react";

const testimonials = [
  {
    name: "Sarah Chen",
    role: "Quantitative Trader",
    company: "Independent",
    image: "/avatars/avatar-1.jpg",
    content: "Impact Radar cut my research time by 70%. The real-time SEC filings with impact scores are game-changing for my swing trading strategy.",
    rating: 5,
  },
  {
    name: "Michael Rodriguez",
    role: "Portfolio Manager",
    company: "Hedge Fund",
    content: "The Market Echo Engine's ML-enhanced predictions have significantly improved our entry timing. The event impact scoring helps me prioritize which filings to read first.",
    rating: 5,
  },
  {
    name: "Dr. Jennifer Park",
    role: "Biotech Investor",
    company: "Venture Capital",
    content: "FDA announcement alerts are instant and accurate. I caught a phase 3 approval 5 minutes before Bloomberg. Paid for itself on the first trade.",
    rating: 5,
  },
  {
    name: "David Thompson",
    role: "Day Trader",
    company: "Full-time Trader",
    content: "Backtesting feature validated my event-driven strategy. Seeing historical accuracy gave me confidence to increase position sizing. ROI is incredible.",
    rating: 5,
  },
  {
    name: "Lisa Martinez",
    role: "Equity Analyst",
    company: "Investment Bank",
    content: "The API integration into our Bloomberg terminals was seamless. Our analysts now have deterministic impact scores alongside traditional metrics.",
    rating: 5,
  },
  {
    name: "James Wilson",
    role: "Options Trader",
    company: "Proprietary Firm",
    content: "Portfolio risk analysis helped me identify correlated exposure I missed. The event timeline visualization is brilliant for earnings season prep.",
    rating: 5,
  },
];

export function Testimonials() {
  return (
    <section className="py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-xl text-center">
          <h2 className="text-base font-semibold leading-7 text-[--primary]">
            Testimonials
          </h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-[--text] sm:text-4xl">
            Trusted by active traders worldwide
          </p>
        </div>
        <div className="mx-auto mt-16 flow-root max-w-2xl sm:mt-20 lg:mx-0 lg:max-w-none">
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {testimonials.map((testimonial, index) => (
              <div
                key={index}
                className="rounded-2xl border border-white/10 bg-[--panel] p-8"
              >
                <div className="flex gap-1 mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star
                      key={i}
                      className="h-5 w-5 fill-yellow-400 text-yellow-400"
                    />
                  ))}
                </div>
                <blockquote className="text-[--muted] text-sm leading-relaxed">
                  "{testimonial.content}"
                </blockquote>
                <div className="mt-6 flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-[--primary] to-blue-600 flex items-center justify-center text-sm font-semibold text-black">
                    {testimonial.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                  </div>
                  <div>
                    <div className="font-semibold text-[--text]">
                      {testimonial.name}
                    </div>
                    <div className="text-sm text-[--muted]">
                      {testimonial.role} · {testimonial.company}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 border-t border-white/10 pt-16">
          <div className="mx-auto max-w-5xl">
            <div className="rounded-3xl border border-[--primary]/20 bg-gradient-to-br from-[--primary]/5 to-blue-600/5 p-8 sm:p-12">
              <div className="text-center mb-8">
                <h3 className="text-2xl sm:text-3xl font-bold text-[--text] mb-3">
                  Market Echo Engine
                </h3>
                <p className="text-[--primary] text-sm font-semibold uppercase tracking-wider">
                  Self-Learning ML Technology
                </p>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
                <div>
                  <h4 className="text-lg font-semibold text-[--text] mb-3">
                    How It Works
                  </h4>
                  <p className="text-[--muted] leading-relaxed">
                    Our proprietary machine learning system continuously learns from real stock price movements after events occur. It analyzes thousands of historical SEC filings, FDA approvals, and corporate announcements to predict actual market impact with verified accuracy across multiple time horizons.
                  </p>
                </div>
                <div>
                  <h4 className="text-lg font-semibold text-[--text] mb-3">
                    Why It Matters
                  </h4>
                  <p className="text-[--muted] leading-relaxed">
                    Unlike static scoring systems, Market Echo Engine gets smarter every day. It identifies which event types historically move stocks, learns from prediction errors, and adjusts impact scores based on real market outcomes across 1-day, 5-day, and 20-day horizons.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-8 border-t border-white/10">
                <div className="text-center">
                  <div className="text-3xl font-bold text-[--primary]">2,670+</div>
                  <div className="mt-1 text-sm text-[--muted]">
                    Verified event outcomes
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-[--primary]">66%</div>
                  <div className="mt-1 text-sm text-[--muted]">
                    1-Day directional accuracy
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-[--primary]">890+</div>
                  <div className="mt-1 text-sm text-[--muted]">
                    Unique tickers covered
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
