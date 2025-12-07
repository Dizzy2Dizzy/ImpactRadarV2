"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, Target, StopCircle, DollarSign, Clock, RefreshCw, Briefcase, AlertCircle, Zap, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TradeRecommendation {
  id: number;
  event_id: number;
  ticker: string;
  recommendation_type: string;
  entry_price_target: number;
  stop_loss: number;
  take_profit: number;
  position_size_pct: number;
  risk_reward_ratio: number;
  rationale: string;
  expires_at: string;
  created_at: string;
}

interface TradeSignalQuota {
  plan: string;
  daily_limit: number;
  used: number;
  remaining: number;
  resets_at: string;
}

export function TradeSignalsTab() {
  const [signals, setSignals] = useState<TradeRecommendation[]>([]);
  const [portfolioSignals, setPortfolioSignals] = useState<TradeRecommendation[]>([]);
  const [watchlistSignals, setWatchlistSignals] = useState<TradeRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'all' | 'portfolio' | 'watchlist'>('all');
  const [generating, setGenerating] = useState(false);
  const [generatingWatchlist, setGeneratingWatchlist] = useState(false);
  const [quota, setQuota] = useState<TradeSignalQuota | null>(null);
  
  useEffect(() => {
    loadSignals();
    loadQuota();
  }, []);

  const loadQuota = async () => {
    try {
      const res = await fetch("/api/proxy/trade-signals/quota");
      if (res.ok) {
        const data = await res.json();
        setQuota(data);
      }
    } catch (err) {
      console.error("Error loading quota:", err);
    }
  };
  
  const loadSignals = async () => {
    try {
      setLoading(true);
      setError(null);
      const [allRes, portfolioRes, watchlistRes] = await Promise.all([
        fetch("/api/proxy/trade-signals").catch(() => ({ ok: false })),
        fetch("/api/proxy/trade-signals/portfolio").catch(() => ({ ok: false })),
        fetch("/api/proxy/trade-signals/watchlist").catch(() => ({ ok: false })),
      ]);
      
      if (allRes.ok) {
        const data = await (allRes as Response).json();
        setSignals(Array.isArray(data) ? data : []);
      } else {
        setSignals([]);
      }
      if (portfolioRes.ok) {
        const data = await (portfolioRes as Response).json();
        setPortfolioSignals(Array.isArray(data) ? data : []);
      } else {
        setPortfolioSignals([]);
      }
      if (watchlistRes.ok) {
        const data = await (watchlistRes as Response).json();
        setWatchlistSignals(Array.isArray(data) ? data : []);
      } else {
        setWatchlistSignals([]);
      }
    } catch (err: any) {
      console.error("Error loading signals:", err);
      setSignals([]);
      setPortfolioSignals([]);
      setWatchlistSignals([]);
    } finally {
      setLoading(false);
    }
  };

  const generateForPortfolio = async () => {
    try {
      setGenerating(true);
      setError(null);
      const res = await fetch("/api/proxy/trade-signals/generate-portfolio", {
        method: "POST",
      });
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = typeof data.detail === 'object' ? data.detail : { error: data.detail || "Failed to generate signals" };
        
        if (detail.code === 'DAILY_LIMIT_EXCEEDED') {
          setError(`Daily signal limit reached (${detail.used}/${detail.daily_limit}). Resets at midnight UTC.`);
          await loadQuota();
          return;
        }
        if (detail.code === 'PLAN_UPGRADE_REQUIRED') {
          setError("Trade signal generation requires a Pro or Team plan. Upgrade to access this feature.");
          return;
        }
        
        const errorMsg = detail.error || data.detail || "Failed to generate signals";
        if (errorMsg.includes("No portfolios found") || errorMsg.includes("No positions")) {
          setError("Please upload a portfolio first in the Portfolio tab to generate personalized trade signals.");
          return;
        }
        if (errorMsg.includes("No recent events")) {
          setError("No recent events found for your portfolio tickers. Check back after new events are detected.");
          return;
        }
        throw new Error(errorMsg);
      }
      
      const result = await res.json();
      if (result.generated_count === 0 && result.skipped_count > 0) {
        setError(null);
      }
      
      await Promise.all([loadSignals(), loadQuota()]);
    } catch (err: any) {
      setError(err.message || "Failed to generate signals. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  const generateForWatchlist = async () => {
    try {
      setGeneratingWatchlist(true);
      setError(null);
      const res = await fetch("/api/proxy/trade-signals/generate-watchlist", {
        method: "POST",
      });
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = typeof data.detail === 'object' ? data.detail : { error: data.detail || "Failed to generate signals" };
        
        if (detail.code === 'DAILY_LIMIT_EXCEEDED') {
          setError(`Daily signal limit reached (${detail.used}/${detail.daily_limit}). Resets at midnight UTC.`);
          await loadQuota();
          return;
        }
        if (detail.code === 'PLAN_UPGRADE_REQUIRED') {
          setError("Trade signal generation requires a Pro or Team plan. Upgrade to access this feature.");
          return;
        }
        
        const errorMsg = detail.error || data.detail || "Failed to generate signals";
        if (errorMsg.includes("No tickers in your watchlist")) {
          setError("Please add stocks to your watchlist first in the Watchlist tab.");
          return;
        }
        if (errorMsg.includes("No recent events")) {
          setError("No recent events found for your watchlist tickers. Check back after new events are detected.");
          return;
        }
        throw new Error(errorMsg);
      }
      
      const result = await res.json();
      if (result.generated_count === 0 && result.skipped_count > 0) {
        setError(null);
      }
      
      await Promise.all([loadSignals(), loadQuota()]);
    } catch (err: any) {
      setError(err.message || "Failed to generate signals. Please try again.");
    } finally {
      setGeneratingWatchlist(false);
    }
  };
  
  const formatPrice = (price: number) => `$${price.toFixed(2)}`;
  
  const getRRColor = (rr: number) => {
    if (rr >= 3) return "text-[--success]";
    if (rr >= 2) return "text-[--warning]";
    return "text-[--error]";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-[--muted]">Loading trade signals...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[--error-light] border border-[--border] rounded-lg p-6">
        <div className="flex items-center gap-2 text-[--error]">
          <AlertCircle className="h-5 w-5" />
          <p>{error}</p>
        </div>
        <Button onClick={loadSignals} variant="outline" className="mt-4">
          Try Again
        </Button>
      </div>
    );
  }
  
  const currentSignals = activeView === 'all' ? signals : activeView === 'portfolio' ? portfolioSignals : watchlistSignals;
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[--text] mb-2">Trade Signals</h2>
          <p className="text-sm text-[--muted]">
            AI-generated trade recommendations with entry/exit targets
          </p>
        </div>
        <div className="flex items-center gap-4">
          {quota && quota.daily_limit > 0 && (
            <div className="text-right">
              <div className="flex items-center gap-1.5 text-sm">
                <Zap className={`h-4 w-4 ${quota.remaining > 0 ? 'text-[--success]' : 'text-[--error]'}`} />
                <span className="text-[--muted]">Daily Quota:</span>
                <span className={`font-semibold ${quota.remaining > 0 ? 'text-[--text]' : 'text-[--error]'}`}>
                  {quota.remaining}/{quota.daily_limit}
                </span>
              </div>
              <p className="text-xs text-[--muted]">
                {quota.plan.charAt(0).toUpperCase() + quota.plan.slice(1)} plan
              </p>
            </div>
          )}
          {activeView === 'portfolio' && (
            <Button
              onClick={generateForPortfolio}
              disabled={generating || (quota?.remaining === 0)}
              className="flex items-center gap-2"
            >
              <Briefcase className="h-4 w-4" />
              {generating ? "Generating..." : "Generate for Portfolio"}
            </Button>
          )}
          {activeView === 'watchlist' && (
            <Button
              onClick={generateForWatchlist}
              disabled={generatingWatchlist || (quota?.remaining === 0)}
              className="flex items-center gap-2"
            >
              <Eye className="h-4 w-4" />
              {generatingWatchlist ? "Generating..." : "Generate for Watchlist"}
            </Button>
          )}
        </div>
      </div>

      <div className="flex gap-2">
        <Button 
          variant={activeView === 'all' ? 'default' : 'outline'} 
          onClick={() => setActiveView('all')}
        >
          All Signals
        </Button>
        <Button 
          variant={activeView === 'portfolio' ? 'default' : 'outline'} 
          onClick={() => setActiveView('portfolio')}
        >
          <Briefcase className="h-4 w-4 mr-2" /> Portfolio
        </Button>
        <Button 
          variant={activeView === 'watchlist' ? 'default' : 'outline'} 
          onClick={() => setActiveView('watchlist')}
        >
          <Eye className="h-4 w-4 mr-2" /> Watchlist
        </Button>
        <Button variant="outline" onClick={loadSignals} className="ml-auto">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {currentSignals.length === 0 ? (
        <div className="text-center py-12 bg-[--surface-muted] rounded-lg">
          <Target className="h-12 w-12 text-[--muted] mx-auto mb-4" />
          <p className="text-[--muted] mb-4">
            {activeView === 'portfolio' 
              ? "No portfolio signals available. Generate signals based on your portfolio."
              : activeView === 'watchlist'
              ? "No watchlist signals available. Generate signals for stocks you're watching."
              : "No trade signals available at this time."}
          </p>
          {activeView === 'portfolio' && (
            <Button onClick={generateForPortfolio} disabled={generating}>
              {generating ? "Generating..." : "Generate Portfolio Signals"}
            </Button>
          )}
          {activeView === 'watchlist' && (
            <Button onClick={generateForWatchlist} disabled={generatingWatchlist}>
              {generatingWatchlist ? "Generating..." : "Generate Watchlist Signals"}
            </Button>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {currentSignals.map((signal) => (
            <div 
              key={signal.id} 
              className={`bg-[--surface-muted] border rounded-lg p-4 hover:bg-[--surface-hover] transition-colors ${
                signal.recommendation_type === 'buy' 
                  ? 'border-[--border]' 
                  : 'border-[--border]'
              }`}
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  {signal.recommendation_type === 'buy' ? (
                    <TrendingUp className="h-5 w-5 text-[--success]" />
                  ) : (
                    <TrendingDown className="h-5 w-5 text-[--error]" />
                  )}
                  <span className="text-lg font-bold text-[--text]">{signal.ticker}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    signal.recommendation_type === 'buy' 
                      ? 'bg-[--success-soft] text-[--success]' 
                      : 'bg-[--error-soft] text-[--error]'
                  }`}>
                    {signal.recommendation_type.toUpperCase()}
                  </span>
                </div>
                <span className="text-xs text-[--muted] flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Expires: {new Date(signal.expires_at).toLocaleDateString()}
                </span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                <div>
                  <span className="text-xs text-[--muted] block">
                    <DollarSign className="h-3 w-3 inline mr-1" />
                    Entry
                  </span>
                  <span className="font-medium text-[--text]">{formatPrice(signal.entry_price_target)}</span>
                </div>
                <div>
                  <span className="text-xs text-[--muted] block">
                    <StopCircle className="h-3 w-3 inline mr-1" />
                    Stop Loss
                  </span>
                  <span className="font-medium text-[--error]">{formatPrice(signal.stop_loss)}</span>
                </div>
                <div>
                  <span className="text-xs text-[--muted] block">
                    <Target className="h-3 w-3 inline mr-1" />
                    Take Profit
                  </span>
                  <span className="font-medium text-[--success]">{formatPrice(signal.take_profit)}</span>
                </div>
                <div>
                  <span className="text-xs text-[--muted] block">R/R Ratio</span>
                  <span className={`font-bold ${getRRColor(signal.risk_reward_ratio)}`}>
                    {signal.risk_reward_ratio.toFixed(1)}:1
                  </span>
                </div>
              </div>
              
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 text-sm border-t border-[--border] pt-3">
                <span className="text-[--muted]">
                  Position Size: <span className="text-[--text] font-medium">{signal.position_size_pct}%</span>
                </span>
                <span className="text-xs text-[--muted] max-w-md truncate" title={signal.rationale}>
                  {signal.rationale}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
