"use client";

import { useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Calendar, Clock, ArrowRight } from "lucide-react";

const blogPosts = [
  {
    slug: "sec-8k-filing-trading-strategy",
    title: "How to Build a Profitable SEC 8-K Filing Trading Strategy",
    excerpt:
      "Learn how professional traders use SEC 8-K filings to identify market-moving events before the crowd. Includes backtested examples and impact scoring methodology.",
    category: "Trading Strategy",
    date: "2025-11-15",
    readTime: "8 min read",
    author: "Impact Radar Research Team",
  },
  {
    slug: "fda-approval-biotech-trading",
    title: "FDA Approval Trading: A Complete Guide for Biotech Investors",
    excerpt:
      "Master the art of trading FDA announcements with this comprehensive guide covering phase trials, approval catalysts, and risk management strategies.",
    category: "Biotech Trading",
    date: "2025-11-12",
    readTime: "10 min read",
    author: "Impact Radar Research Team",
  },
  {
    slug: "market-echo-engine-ml-predictions",
    title: "Market Echo Engine: How Machine Learning Improves Event Predictions",
    excerpt:
      "Deep dive into Impact Radar's self-learning ML system that achieves 85%+ directional accuracy on SEC 8-K events by learning from actual price movements.",
    category: "Technology",
    date: "2025-11-10",
    readTime: "12 min read",
    author: "Impact Radar Research Team",
  },
  {
    slug: "event-driven-portfolio-risk",
    title: "Managing Event-Driven Portfolio Risk in Volatile Markets",
    excerpt:
      "Discover how to use correlation analysis and event exposure metrics to protect your portfolio during earnings season and major announannouncements.",
    category: "Risk Management",
    date: "2025-11-08",
    readTime: "9 min read",
    author: "Impact Radar Research Team",
  },
  {
    slug: "backtesting-event-impact-scores",
    title: "Backtesting Event Impact Scores: Validating Your Trading Edge",
    excerpt:
      "Step-by-step guide to validating event-driven strategies using historical data, SPY-normalized returns, and multi-horizon analysis.",
    category: "Analytics",
    date: "2025-11-05",
    readTime: "11 min read",
    author: "Impact Radar Research Team",
  },
  {
    slug: "real-time-alerts-active-trading",
    title: "Setting Up Real-Time Alerts for Active Trading Success",
    excerpt:
      "Configure custom alerts for SEC filings, earnings, M&A activity, and FDA announcements to never miss a trading opportunity.",
    category: "Platform Guide",
    date: "2025-11-03",
    readTime: "7 min read",
    author: "Impact Radar Research Team",
  },
];

const categories = ["All Posts", "Trading Strategy", "Biotech Trading", "Technology", "Risk Management", "Analytics", "Platform Guide"];

export default function BlogPage() {
  const [selectedCategory, setSelectedCategory] = useState("All Posts");

  const filteredPosts = selectedCategory === "All Posts"
    ? blogPosts
    : blogPosts.filter(post => post.category === selectedCategory);

  return (
    <div className="min-h-screen bg-[--background]">
      <Header />
      <main className="pt-24 pb-16">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <h1 className="text-4xl md:text-6xl font-bold text-[--text] mb-4">
              Trading Insights & <span className="text-[--primary]">Market Analysis</span>
            </h1>
            <p className="text-lg text-[--muted] max-w-2xl mx-auto">
              Expert strategies, backtesting guides, and platform tutorials for
              event-driven traders
            </p>
          </div>

          <div className="flex gap-4 mb-12 overflow-x-auto pb-2">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`px-4 py-2 rounded-lg whitespace-nowrap text-sm font-medium transition-colors ${
                  category === selectedCategory
                    ? "bg-[--primary] text-black"
                    : "bg-[--panel] text-[--muted] hover:text-[--text] border border-white/10"
                }`}
              >
                {category}
              </button>
            ))}
          </div>

          {filteredPosts.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-[--muted]">No posts found in this category.</p>
            </div>
          ) : (
            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
              {filteredPosts.map((post) => (
                <Link
                  key={post.slug}
                  href={`/blog/${post.slug}`}
                  className="group rounded-2xl border border-white/10 bg-[--panel] overflow-hidden hover:border-[--primary]/50 transition-all"
                >
                  <div className="h-48 bg-gradient-to-br from-[--primary]/20 to-blue-600/20 flex items-center justify-center">
                    <div className="text-6xl font-bold text-[--primary]/20">
                      {post.category.slice(0, 2).toUpperCase()}
                    </div>
                  </div>
                  <div className="p-6">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs font-medium text-[--primary]">
                        {post.category}
                      </span>
                      <span className="text-xs text-[--muted]">•</span>
                      <span className="text-xs text-[--muted] flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {post.readTime}
                      </span>
                    </div>
                    <h2 className="text-xl font-semibold text-[--text] mb-2 group-hover:text-[--primary] transition-colors">
                      {post.title}
                    </h2>
                    <p className="text-sm text-[--muted] mb-4 line-clamp-3">
                      {post.excerpt}
                    </p>
                    <div className="flex items-center justify-between pt-4 border-t border-white/5">
                      <div className="flex items-center gap-2 text-xs text-[--muted]">
                        <Calendar className="h-3 w-3" />
                        {new Date(post.date).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </div>
                      <span className="text-sm text-[--primary] flex items-center gap-1 group-hover:gap-2 transition-all">
                        Read more <ArrowRight className="h-4 w-4" />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          <div className="mt-16 text-center">
            <p className="text-[--muted] mb-6">
              Want to stay updated with the latest trading insights?
            </p>
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 rounded-lg bg-[--primary] px-6 py-3 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
            >
              Subscribe to Newsletter
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
