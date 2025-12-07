"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { ArrowUpRight, ArrowDownRight, Minus, Clock, TrendingUp } from "lucide-react";

interface Event {
  id: number;
  ticker: string;
  company_name: string;
  event_type: string;
  title: string;
  date: string;
  source_url: string | null;
  impact_score: number;
  direction: string | null;
  sector: string | null;
  detected_at: string | null;
}

export default function PublicEventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [sectorFilter, setSectorFilter] = useState("");
  const [directionFilter, setDirectionFilter] = useState("");
  const [minScoreFilter, setMinScoreFilter] = useState(0);

  useEffect(() => {
    fetchEvents();
  }, [sectorFilter, directionFilter, minScoreFilter]);

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8080';
      
      const params = new URLSearchParams();
      params.append('limit', '50');
      if (sectorFilter) params.append('sector', sectorFilter);
      if (directionFilter) params.append('direction', directionFilter);
      if (minScoreFilter > 0) params.append('min_impact', minScoreFilter.toString());
      
      const response = await fetch(`${backendUrl}/events/public?${params.toString()}`);
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error('Error fetching events:', error);
    } finally {
      setLoading(false);
    }
  };

  const getDirectionIcon = (direction: string | null) => {
    if (direction === 'positive') return <ArrowUpRight className="h-4 w-4 text-[--success]" />;
    if (direction === 'negative') return <ArrowDownRight className="h-4 w-4 text-[--error]" />;
    return <Minus className="h-4 w-4 text-[--neutral]" />;
  };

  const getDirectionColor = (direction: string | null) => {
    if (direction === 'positive') return 'text-[--success]';
    if (direction === 'negative') return 'text-[--error]';
    return 'text-[--neutral]';
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'bg-[--error]/20 text-[--error] border-[--error]/30';
    if (score >= 60) return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    if (score >= 40) return 'bg-[--warning]/20 text-[--warning] border-[--warning]/30';
    return 'bg-[--neutral]/20 text-[--neutral] border-[--neutral]/30';
  };

  const getTimeAgo = (detectedAt: string | null, eventDate: string) => {
    const timestamp = detectedAt || eventDate;
    const now = new Date();
    const detected = new Date(timestamp);
    const diffMs = now.getTime() - detected.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `Detected ${diffMins} minutes ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `Detected ${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `Detected ${diffDays} days ago`;
  };

  const uniqueSectors = Array.from(new Set(events.map(e => e.sector).filter(Boolean))) as string[];

  return (
    <div className="min-h-screen bg-[--bg]">
      <Header />
      
      <main className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-semibold text-[--text] mb-4">
            Live Events Feed
          </h1>
          <p className="text-lg text-[--muted] max-w-2xl">
            Real-time market-moving events from SEC filings, FDA approvals, and company announcements. 
            Track events before they hit social media.
          </p>
        </div>

        <div className="mb-8 p-6 rounded-2xl border border-[--primary]/20 bg-[--primary]/5">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="h-6 w-6 text-[--primary]" />
            <h2 className="text-xl font-semibold text-[--text]">Get Ahead of the Market</h2>
          </div>
          <p className="text-[--muted] mb-4">
            These events were detected 15+ minutes before appearing on Twitter. 
            Sign up to receive instant alerts and never miss a profitable opportunity.
          </p>
          <Button asChild className="bg-[--primary] hover:bg-[--primary-contrast] text-black hover:text-white">
            <Link href="/signup">Get Instant Alerts - Start Free Trial</Link>
          </Button>
        </div>

        <div className="mb-6 flex flex-wrap gap-4">
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="px-4 py-2 rounded-lg bg-[--panel] border border-white/10 text-[--text] focus:outline-none focus:border-[--primary]/50"
          >
            <option value="">All Sectors</option>
            {uniqueSectors.map(sector => (
              <option key={sector} value={sector}>{sector}</option>
            ))}
          </select>

          <select
            value={directionFilter}
            onChange={(e) => setDirectionFilter(e.target.value)}
            className="px-4 py-2 rounded-lg bg-[--panel] border border-white/10 text-[--text] focus:outline-none focus:border-[--primary]/50"
          >
            <option value="">All Directions</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="neutral">Neutral</option>
          </select>

          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(Number(e.target.value))}
            className="px-4 py-2 rounded-lg bg-[--panel] border border-white/10 text-[--text] focus:outline-none focus:border-[--primary]/50"
          >
            <option value="0">All Impact Scores</option>
            <option value="40">40+ Medium Impact</option>
            <option value="60">60+ High Impact</option>
            <option value="75">75+ Critical Impact</option>
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[--primary]"></div>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-[--panel]">
            <table className="w-full">
              <thead className="border-b border-white/10">
                <tr className="text-left">
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Ticker</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Event Type</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Title</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Impact</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Direction</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Time</th>
                  <th className="px-4 py-3 text-sm font-medium text-[--muted]">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {events.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-[--muted]">
                      No events found matching your filters.
                    </td>
                  </tr>
                ) : (
                  events.map((event) => (
                    <tr key={event.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono font-semibold text-[--primary]">
                          ${event.ticker}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-sm text-[--text] capitalize">
                          {event.event_type.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="px-4 py-3 max-w-md">
                        <div className="text-sm text-[--text] truncate" title={event.title}>
                          {event.title}
                        </div>
                        <div className="text-xs text-[--muted] truncate">
                          {event.company_name}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-sm font-semibold border ${getScoreColor(event.impact_score)}`}>
                          {event.impact_score}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {getDirectionIcon(event.direction)}
                          <span className={`text-sm capitalize ${getDirectionColor(event.direction)}`}>
                            {event.direction || 'neutral'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 text-sm text-[--muted]">
                          <Clock className="h-3.5 w-3.5" />
                          <span className="whitespace-nowrap">
                            {getTimeAgo(event.detected_at, event.date)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {event.source_url ? (
                          <a
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-sm text-[--primary] hover:underline"
                          >
                            View
                            <ArrowUpRight className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-sm text-[--muted]">-</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-8 p-6 rounded-2xl border border-[--primary]/20 bg-gradient-to-br from-[--primary]/10 to-[--accent]/10">
          <h2 className="text-2xl font-semibold text-[--text] mb-3">
            Want instant notifications for high-impact events?
          </h2>
          <p className="text-[--muted] mb-4">
            Join 500+ active traders who get alerts 15 minutes before social media. 
            Never miss a market-moving opportunity again.
          </p>
          <div className="flex gap-4">
            <Button asChild className="bg-[--primary] hover:bg-[--primary-contrast] text-black hover:text-white">
              <Link href="/signup">Start Free Trial</Link>
            </Button>
            <Button asChild variant="outline" className="border-white/10">
              <Link href="/pricing">View Plans</Link>
            </Button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
