"use client";

import { useState, useEffect } from "react";
import { User, CreditCard, Activity, TrendingUp, Calendar, AlertCircle, Sliders, LogOut, Mail, Lock, Phone, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { showToast } from "@/lib/toast";
import { ScoringPreferencesModal } from "./ScoringPreferencesModal";
import { ModelVersionFilter } from './ModelVersionFilter';
import { DisplayVersion } from './ImpactScoreBadge';

interface AccountSummary {
  user_id: number;
  email: string;
  plan: string;
  trial_ends_at: string | null;
  account_created_at: string;
  last_login: string | null;
  total_watchlist_companies: number;
  total_alerts_configured: number;
  total_events_viewed: number;
}

interface PerformanceMetrics {
  total_portfolio_value: number;
  total_positions: number;
  events_this_month: number;
  events_matched_to_portfolio: number;
}

interface ActivityItem {
  type: string;
  description: string;
  timestamp: string;
  details?: any;
}

interface Holding {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  total_value: number;
  profit_loss: number;
  profit_loss_percent: number;
  events_count: number;
}

interface PortfolioPerformance {
  holdings: Holding[];
  total_invested: number;
  current_value: number;
  total_profit_loss: number;
  total_return_percent: number;
}

interface WatchlistInsight {
  ticker: string;
  company_name: string;
  events_tracked: number;
  high_impact_events: number;
  avg_impact_score: number;
  price_change_30d: number;
}

interface EventStats {
  total_events_tracked: number;
  high_impact_events: number;
  portfolio_events: number;
  watchlist_events: number;
}

interface DiagnosticsData {
  portfolio_performance: PortfolioPerformance;
  watchlist_performance: WatchlistInsight[];
  event_stats: EventStats;
}

interface ModelHealth {
  total_groups: number;
  avg_sample_size: number;
  last_updated: string | null;
  coverage: {
    event_types: number;
    sectors: number;
  };
}

export function AccountTab() {
  const [summary, setSummary] = useState<AccountSummary | null>(null);
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsData | null>(null);
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
  const [modelHealthLoading, setModelHealthLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scoringModalOpen, setScoringModalOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');
  
  // Account management modals
  const [changeEmailModal, setChangeEmailModal] = useState(false);
  const [changePasswordModal, setChangePasswordModal] = useState(false);
  const [changePhoneModal, setChangePhoneModal] = useState(false);
  const [cancelSubscriptionModal, setCancelSubscriptionModal] = useState(false);
  
  // Form states
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [submitting, setSubmitting] = useState(false);
  
  const router = useRouter();

  useEffect(() => {
    loadAccountData();
    loadDiagnostics();
    loadModelHealth();
  }, []);

  const loadDiagnostics = async () => {
    try {
      setDiagnosticsLoading(true);
      console.log("[AccountTab] Loading diagnostics from /api/proxy/account/diagnostics");
      
      const res = await fetch("/api/proxy/account/diagnostics");
      console.log("[AccountTab] Diagnostics response status:", res.status, res.statusText);
      
      if (res.ok) {
        const data = await res.json();
        console.log("[AccountTab] Diagnostics data received:", {
          holdingsCount: data?.portfolio_performance?.holdings?.length || 0,
          totalInvested: data?.portfolio_performance?.total_invested || 0,
          watchlistCount: data?.watchlist_performance?.length || 0
        });
        setDiagnostics(data);
      } else {
        const errorText = await res.text().catch(() => 'Unknown error');
        console.error("[AccountTab] Failed to load diagnostics:", res.status, errorText);
      }
    } catch (err) {
      console.error("[AccountTab] Exception while loading diagnostics:", err);
    } finally {
      setDiagnosticsLoading(false);
    }
  };

  const loadModelHealth = async () => {
    try {
      setModelHealthLoading(true);
      const res = await fetch("/api/proxy/account/model-health");
      if (res.ok) {
        const data = await res.json();
        setModelHealth(data);
      }
    } catch (err) {
      console.error("Failed to load model health:", err);
    } finally {
      setModelHealthLoading(false);
    }
  };

  const loadAccountData = async () => {
    const timeout = 15000; // 15 second timeout
    
    try {
      setLoading(true);
      setError(null);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      try {
        const results = await Promise.allSettled([
          fetch("/api/proxy/account/summary", { signal: controller.signal }),
          fetch("/api/proxy/account/performance", { signal: controller.signal }),
          fetch("/api/proxy/account/activity", { signal: controller.signal }),
        ]);

        clearTimeout(timeoutId);

        const [summaryResult, performanceResult, activityResult] = results;

        if (summaryResult.status === 'fulfilled' && summaryResult.value.ok) {
          const summaryData = await summaryResult.value.json();
          setSummary(summaryData);
        } else {
          console.warn("Failed to load account summary:", summaryResult);
        }

        if (performanceResult.status === 'fulfilled' && performanceResult.value.ok) {
          const performanceData = await performanceResult.value.json();
          setPerformance(performanceData);
        } else {
          console.warn("Failed to load performance data:", performanceResult);
          setPerformance({
            total_portfolio_value: 0,
            total_positions: 0,
            events_this_month: 0,
            events_matched_to_portfolio: 0,
          });
        }

        if (activityResult.status === 'fulfilled' && activityResult.value.ok) {
          const activityData = await activityResult.value.json();
          setActivities(activityData.activities || []);
        } else {
          console.warn("Failed to load activity data:", activityResult);
          setActivities([]);
        }

        if (summaryResult.status === 'rejected' || (summaryResult.status === 'fulfilled' && !summaryResult.value.ok)) {
          throw new Error("Failed to load account summary. Please try again or contact support.");
        }
      } catch (fetchErr: any) {
        clearTimeout(timeoutId);
        if (fetchErr.name === 'AbortError') {
          throw new Error("Request timed out. Please try again.");
        }
        throw fetchErr;
      }
    } catch (err: any) {
      console.error("Failed to load account data:", err);
      setError(err?.message || "Failed to load account data");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case "team":
        return "text-purple-400";
      case "pro":
        return "text-blue-400";
      default:
        return "text-[--muted]";
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "alert_triggered":
        return <AlertCircle className="h-4 w-4 text-[--warning]" />;
      case "portfolio_uploaded":
        return <TrendingUp className="h-4 w-4 text-[--success]" />;
      case "watchlist_added":
        return <Activity className="h-4 w-4 text-[--primary]" />;
      default:
        return <Activity className="h-4 w-4 text-[--muted]" />;
    }
  };

  const handleLogout = async () => {
    try {
      setIsLoggingOut(true);
      const response = await fetch("/api/auth/logout", {
        method: "POST",
      });
      
      if (response.ok) {
        showToast("Logged out successfully", "success");
        router.push("/");
      } else {
        throw new Error("Logout failed");
      }
    } catch (error) {
      console.error("Logout error:", error);
      showToast("Failed to logout. Please try again.", "error");
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleChangeEmail = async () => {
    if (!newEmail || !currentPassword) {
      showToast("Please fill in all fields", "error");
      return;
    }
    
    try {
      setSubmitting(true);
      const response = await fetch("/api/proxy/account/change-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newEmail, currentPassword }),
      });
      
      if (response.ok) {
        showToast("Email updated successfully. Please verify your new email.", "success");
        setChangeEmailModal(false);
        setNewEmail("");
        setCurrentPassword("");
        await loadAccountData();
      } else {
        const data = await response.json();
        throw new Error(data.message || "Failed to update email");
      }
    } catch (error: any) {
      showToast(error.message || "Failed to update email", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast("Please fill in all fields", "error");
      return;
    }
    
    if (newPassword !== confirmPassword) {
      showToast("New passwords do not match", "error");
      return;
    }
    
    if (newPassword.length < 8) {
      showToast("Password must be at least 8 characters", "error");
      return;
    }
    
    try {
      setSubmitting(true);
      const response = await fetch("/api/proxy/account/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currentPassword, newPassword }),
      });
      
      if (response.ok) {
        showToast("Password updated successfully", "success");
        setChangePasswordModal(false);
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        const data = await response.json();
        throw new Error(data.message || "Failed to update password");
      }
    } catch (error: any) {
      showToast(error.message || "Failed to update password", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChangePhone = async () => {
    if (!phoneNumber) {
      showToast("Please enter a phone number", "error");
      return;
    }
    
    // Basic E.164 format validation
    if (!phoneNumber.match(/^\+[1-9]\d{1,14}$/)) {
      showToast("Please enter a valid phone number in E.164 format (e.g., +14155551234)", "error");
      return;
    }
    
    try {
      setSubmitting(true);
      const response = await fetch("/api/proxy/account/change-phone", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_phone: phoneNumber }),
      });
      
      if (response.ok) {
        showToast("Phone number updated successfully", "success");
        setChangePhoneModal(false);
        setPhoneNumber("");
        await loadAccountData();
      } else {
        const data = await response.json();
        throw new Error(data.message || "Failed to update phone number");
      }
    } catch (error: any) {
      showToast(error.message || "Failed to update phone number", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setSubmitting(true);
      const response = await fetch("/api/proxy/account/cancel-subscription", {
        method: "POST",
      });
      
      if (response.ok) {
        showToast("Subscription cancelled successfully. You can continue using your plan until the end of the billing period.", "success");
        setCancelSubscriptionModal(false);
        await loadAccountData();
      } else {
        const data = await response.json();
        throw new Error(data.message || "Failed to cancel subscription");
      }
    } catch (error: any) {
      showToast(error.message || "Failed to cancel subscription", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading account information...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-8 text-center">
        <h2 className="text-xl font-semibold text-[--error] mb-2">Error</h2>
        <p className="text-[--error]">{error}</p>
        <Button onClick={loadAccountData} variant="outline" className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  const isTrialActive = summary?.trial_ends_at && new Date(summary.trial_ends_at) > new Date();
  const daysUntilTrialEnds = summary?.trial_ends_at
    ? Math.ceil((new Date(summary.trial_ends_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Account</h2>
          <p className="text-sm text-[--muted]">
            Manage your account settings and view usage statistics
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
          <Button
            variant="outline"
            onClick={() => setScoringModalOpen(true)}
            className="flex items-center gap-2"
          >
            <Sliders className="h-4 w-4" />
            Customize Scoring
          </Button>
          {summary?.plan === "free" && (
            <Button asChild>
              <Link href="/pricing">Upgrade Plan</Link>
            </Button>
          )}
        </div>
      </div>

      {/* Trial Notice */}
      {isTrialActive && (
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-4">
          <div className="flex items-start gap-3">
            <Calendar className="h-5 w-5 text-[--primary] mt-0.5" />
            <div>
              <h3 className="font-medium text-[--primary]">Trial Active</h3>
              <p className="text-sm text-[--primary]">
                Your {summary?.plan} plan trial expires in {daysUntilTrialEnds} days (
                {formatDate(summary?.trial_ends_at || "")})
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Account Summary Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <button
          onClick={() => setChangeEmailModal(true)}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 hover:bg-[--surface-hover] hover:border-[--border-strong] transition-all cursor-pointer text-left group"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--primary]">
              <User className="h-6 w-6" />
            </span>
            <Mail className="h-4 w-4 text-[--muted] group-hover:text-[--primary] transition-colors" />
          </div>
          <div className="text-sm text-[--muted] mb-1">Email</div>
          <div className="text-lg font-semibold text-[--text] truncate">{summary?.email}</div>
          <div className="text-xs text-[--primary] mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            Click to change
          </div>
        </button>

        <button
          onClick={() => summary?.plan === "free" ? router.push("/pricing") : setCancelSubscriptionModal(true)}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 hover:bg-[--surface-hover] hover:border-purple-400/50 transition-all cursor-pointer text-left group"
        >
          <div className="flex items-center justify-between mb-4">
            <span className={getPlanColor(summary?.plan || "free")}>
              <CreditCard className="h-6 w-6" />
            </span>
            <span className={`text-xs ${getPlanColor(summary?.plan || "free")} opacity-0 group-hover:opacity-100 transition-opacity`}>
              {summary?.plan === "free" ? "Upgrade" : "Manage"}
            </span>
          </div>
          <div className="text-sm text-[--muted] mb-1">Plan</div>
          <div className={`text-lg font-semibold ${getPlanColor(summary?.plan || "free")} uppercase`}>
            {summary?.plan || "free"}
          </div>
          <div className={`text-xs ${getPlanColor(summary?.plan || "free")} mt-2 opacity-0 group-hover:opacity-100 transition-opacity`}>
            {summary?.plan === "free" ? "Click to upgrade" : "Click to manage subscription"}
          </div>
        </button>

        <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--success]">
              <Activity className="h-6 w-6" />
            </span>
          </div>
          <div className="text-sm text-[--muted] mb-1">Member Since</div>
          <div className="text-lg font-semibold text-[--text]">
            {formatDate(summary?.account_created_at || "")}
          </div>
        </div>

        <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <div className="flex items-center justify-between mb-4">
            <span className="text-purple-400">
              <Calendar className="h-6 w-6" />
            </span>
          </div>
          <div className="text-sm text-[--muted] mb-1">Last Login</div>
          <div className="text-lg font-semibold text-[--text]">
            {formatDate(summary?.last_login || "")}
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <h3 className="text-lg font-semibold text-[--text] mb-6">Usage & Performance</h3>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="text-sm text-[--muted] mb-2">Watchlist Companies</div>
            <div className="text-3xl font-bold text-[--text]">
              {summary?.total_watchlist_companies || 0}
            </div>
          </div>

          <div>
            <div className="text-sm text-[--muted] mb-2">Active Alerts</div>
            <div className="text-3xl font-bold text-[--text]">
              {summary?.total_alerts_configured || 0}
            </div>
          </div>

          <div>
            <div className="text-sm text-[--muted] mb-2">Portfolio Positions</div>
            <div className="text-3xl font-bold text-[--text]">
              {performance?.total_positions || 0}
            </div>
            {performance && performance.total_positions > 0 && (
              <div className="text-xs text-[--muted] mt-1">
                Value: ${performance.total_portfolio_value.toLocaleString()}
              </div>
            )}
          </div>

          <div>
            <div className="text-sm text-[--muted] mb-2">Events This Month</div>
            <div className="text-3xl font-bold text-[--text]">
              {performance?.events_this_month || 0}
            </div>
            {performance && performance.events_matched_to_portfolio > 0 && (
              <div className="text-xs text-[--success] mt-1">
                {performance.events_matched_to_portfolio} matched to portfolio
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Impact Model Health */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-[--text]">Impact Model Health</h3>
          {modelHealthLoading && (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[--primary]"></div>
          )}
        </div>
        {modelHealth && modelHealth.total_groups !== null && modelHealth.total_groups !== undefined ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="text-sm text-[--muted] mb-2">Groups Trained</div>
              <div className="text-3xl font-bold text-[--text]">
                {modelHealth.total_groups || 0}
              </div>
            </div>

            <div>
              <div className="text-sm text-[--muted] mb-2">Avg Sample Size</div>
              <div className="text-3xl font-bold text-[--text]">
                {modelHealth.avg_sample_size ? Math.round(modelHealth.avg_sample_size) : 0}
              </div>
            </div>

            <div>
              <div className="text-sm text-[--muted] mb-2">Event Types</div>
              <div className="text-3xl font-bold text-[--text]">
                {modelHealth.coverage?.event_types || 0}
              </div>
            </div>

            <div>
              <div className="text-sm text-[--muted] mb-2">Last Updated</div>
              <div className="text-sm text-[--text]">
                {modelHealth.last_updated ? formatDate(modelHealth.last_updated) : 'Never'}
              </div>
              {modelHealth.coverage?.sectors && modelHealth.coverage.sectors > 0 && (
                <div className="text-xs text-[--muted] mt-1">
                  {modelHealth.coverage.sectors} sectors covered
                </div>
              )}
            </div>
          </div>
        ) : modelHealthLoading ? (
          <p className="text-sm text-[--muted] py-4">Loading model health data...</p>
        ) : (
          <div className="text-center py-8">
            <p className="text-sm text-[--muted]">No model health data available</p>
            <p className="text-xs text-[--muted] mt-2">Model training may not have run yet</p>
          </div>
        )}
      </div>

      {/* Recent Activity */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <h3 className="text-lg font-semibold text-[--text] mb-6">Recent Activity</h3>
        {activities.length === 0 ? (
          <p className="text-sm text-[--muted] py-8 text-center">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {activities.map((activity, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 p-4 rounded-lg bg-[--surface-strong] border border-[--border-muted] hover:bg-[--surface-hover] transition-colors"
              >
                <div className="mt-1">{getActivityIcon(activity.type)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[--text] font-medium">{activity.description}</p>
                  <p className="text-xs text-[--muted] mt-1">{formatDateTime(activity.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Diagnostics Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[--text]">Portfolio Diagnostics</h2>
            <p className="text-sm text-[--muted]">
              Real-time portfolio performance tracking with event correlation analysis
            </p>
          </div>
          {diagnosticsLoading && (
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[--primary]"></div>
          )}
        </div>

        {/* Info Banner - Always show to explain what diagnostics are */}
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-[--primary] mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-semibold text-[--primary] mb-1">What are Portfolio Diagnostics?</p>
              <p className="text-[--primary]">
                Diagnostics show how market events affect your holdings in real-time. Track profits/losses for each position, 
                see which events impacted your watchlist tickers, and analyze the correlation between event scores and price movements. 
                This helps you make data-driven decisions based on how similar events have historically affected your portfolio.
              </p>
            </div>
          </div>
        </div>

        {!diagnosticsLoading && (!diagnostics || (diagnostics && diagnostics.portfolio_performance.holdings.length === 0 && diagnostics.watchlist_performance.length === 0)) && (
          <div className="rounded-2xl border border-[--border] bg-[--panel] p-12 text-center">
            <TrendingUp className="h-12 w-12 text-[--muted] mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-[--text] mb-2">No Portfolio Data Yet</h3>
            <p className="text-sm text-[--muted] max-w-md mx-auto mb-4">
              Upload your portfolio in the Portfolio tab to start tracking performance and event correlations. 
              Add companies to your watchlist to monitor events that may impact your holdings.
            </p>
            <div className="flex gap-3 justify-center">
              <Button onClick={loadDiagnostics} variant="outline" size="sm">
                Refresh
              </Button>
              <Link href="/dashboard?tab=portfolio">
                <Button size="sm">Upload Portfolio</Button>
              </Link>
            </div>
          </div>
        )}

        {diagnostics && (
          <>
            {/* Portfolio Performance Card */}
            <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
              <h3 className="text-lg font-semibold text-[--text] mb-6">Portfolio Performance</h3>
              
              {/* Total Summary */}
              <div className="grid gap-4 md:grid-cols-4 mb-6">
                <div>
                  <div className="text-sm text-[--muted] mb-1">Total Invested</div>
                  <div className="text-2xl font-bold text-[--text]">
                    ${diagnostics.portfolio_performance.total_invested.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-[--muted] mb-1">Current Value</div>
                  <div className="text-2xl font-bold text-[--text]">
                    ${diagnostics.portfolio_performance.current_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-[--muted] mb-1">Total Profit/Loss</div>
                  <div className={`text-2xl font-bold ${diagnostics.portfolio_performance.total_profit_loss >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                    {diagnostics.portfolio_performance.total_profit_loss >= 0 ? '+' : ''}${diagnostics.portfolio_performance.total_profit_loss.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-[--muted] mb-1">Total Return</div>
                  <div className={`text-2xl font-bold ${diagnostics.portfolio_performance.total_return_percent >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                    {diagnostics.portfolio_performance.total_return_percent >= 0 ? '+' : ''}{diagnostics.portfolio_performance.total_return_percent.toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Holdings Table */}
              {diagnostics.portfolio_performance.holdings.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[--border]">
                        <th className="text-left py-3 px-2 text-[--muted] font-medium">Ticker</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Quantity</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Avg Cost</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Current Price</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Total Value</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">P/L ($)</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">P/L (%)</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Events</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diagnostics.portfolio_performance.holdings.map((holding, idx) => (
                        <tr key={idx} className="border-b border-[--border-muted] hover:bg-[--surface-hover]">
                          <td className="py-3 px-2 text-[--text] font-medium">{holding.ticker}</td>
                          <td className="py-3 px-2 text-[--text] text-right">{holding.quantity.toLocaleString()}</td>
                          <td className="py-3 px-2 text-[--text] text-right">${holding.avg_cost.toFixed(2)}</td>
                          <td className="py-3 px-2 text-[--text] text-right">${holding.current_price.toFixed(2)}</td>
                          <td className="py-3 px-2 text-[--text] text-right">${holding.total_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                          <td className={`py-3 px-2 text-right font-medium ${holding.profit_loss >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                            {holding.profit_loss >= 0 ? '+' : ''}${holding.profit_loss.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                          </td>
                          <td className={`py-3 px-2 text-right font-medium ${holding.profit_loss_percent >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                            {holding.profit_loss_percent >= 0 ? '+' : ''}{holding.profit_loss_percent.toFixed(2)}%
                          </td>
                          <td className="py-3 px-2 text-[--muted] text-right">{holding.events_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-[--muted] py-8 text-center">No portfolio holdings found. Upload your portfolio to see performance.</p>
              )}
            </div>

            {/* Watchlist Insights Card */}
            <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
              <h3 className="text-lg font-semibold text-[--text] mb-6">Watchlist Insights</h3>
              
              {diagnostics.watchlist_performance.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[--border]">
                        <th className="text-left py-3 px-2 text-[--muted] font-medium">Ticker</th>
                        <th className="text-left py-3 px-2 text-[--muted] font-medium">Company</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Events Tracked</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">High Impact</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">Avg Impact Score</th>
                        <th className="text-right py-3 px-2 text-[--muted] font-medium">30d Price Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diagnostics.watchlist_performance.map((insight, idx) => (
                        <tr key={idx} className="border-b border-[--border-muted] hover:bg-[--surface-hover]">
                          <td className="py-3 px-2 text-[--text] font-medium">{insight.ticker}</td>
                          <td className="py-3 px-2 text-[--text]">{insight.company_name}</td>
                          <td className="py-3 px-2 text-[--text] text-right">{insight.events_tracked}</td>
                          <td className="py-3 px-2 text-[--text] text-right">{insight.high_impact_events}</td>
                          <td className="py-3 px-2 text-[--text] text-right">{insight.avg_impact_score.toFixed(1)}</td>
                          <td className={`py-3 px-2 text-right font-medium ${insight.price_change_30d >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                            {insight.price_change_30d >= 0 ? '+' : ''}{insight.price_change_30d.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm text-[--muted] py-8 text-center">No watchlist items found. Add tickers to your watchlist to see insights.</p>
              )}
            </div>

            {/* Event Impact Summary */}
            <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
              <h3 className="text-lg font-semibold text-[--text] mb-6">Event Impact Summary</h3>
              
              <div className="grid gap-6 md:grid-cols-4">
                <div>
                  <div className="text-sm text-[--muted] mb-2">Total Events Tracked</div>
                  <div className="text-3xl font-bold text-[--text]">
                    {diagnostics.event_stats.total_events_tracked}
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-[--muted] mb-2">High Impact Events</div>
                  <div className="text-3xl font-bold text-[--warning]">
                    {diagnostics.event_stats.high_impact_events}
                  </div>
                  <div className="text-xs text-[--muted] mt-1">
                    Score &gt;= 70
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-[--muted] mb-2">Portfolio Events</div>
                  <div className="text-3xl font-bold text-[--success]">
                    {diagnostics.event_stats.portfolio_events}
                  </div>
                  <div className="text-xs text-[--muted] mt-1">
                    Matched to holdings
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-[--muted] mb-2">Watchlist Events</div>
                  <div className="text-3xl font-bold text-[--primary]">
                    {diagnostics.event_stats.watchlist_events}
                  </div>
                  <div className="text-xs text-[--muted] mt-1">
                    Matched to watchlist
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Account Actions */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Account Management</h3>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Button
            onClick={() => setChangePasswordModal(true)}
            variant="outline"
            className="flex items-center gap-2 justify-start"
          >
            <Lock className="h-4 w-4" />
            Change Password
          </Button>
          <Button
            onClick={() => setChangePhoneModal(true)}
            variant="outline"
            className="flex items-center gap-2 justify-start"
          >
            <Phone className="h-4 w-4" />
            {summary?.plan === "free" ? "Add Phone Number (Pro)" : "Manage Phone Number"}
          </Button>
          {summary?.plan === "free" && (
            <Button asChild className="flex items-center gap-2">
              <Link href="/pricing">
                <CreditCard className="h-4 w-4" />
                Upgrade Plan
              </Link>
            </Button>
          )}
          {summary?.plan && summary?.plan !== "free" && (
            <Button
              onClick={() => setCancelSubscriptionModal(true)}
              variant="outline"
              className="flex items-center gap-2 justify-start text-[--error] hover:text-[--error]"
            >
              <X className="h-4 w-4" />
              Cancel Subscription
            </Button>
          )}
          <Button
            onClick={handleLogout}
            disabled={isLoggingOut}
            variant="outline"
            className="flex items-center gap-2 justify-start"
          >
            <LogOut className="h-4 w-4" />
            {isLoggingOut ? "Logging out..." : "Logout"}
          </Button>
        </div>
      </div>

      {/* Plan Actions */}
      {summary?.plan === "free" && (
        <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-8 text-center">
          <h3 className="text-xl font-semibold text-[--text] mb-2">Upgrade to Pro</h3>
          <p className="text-sm text-[--muted] mb-6">
            Unlock advanced features including unlimited alerts, portfolio insights, and priority support
          </p>
          <Button size="lg" asChild>
            <Link href="/pricing">View Plans</Link>
          </Button>
        </div>
      )}

      {/* Change Email Modal */}
      <Dialog open={changeEmailModal} onOpenChange={setChangeEmailModal}>
        <DialogContent className="bg-[--panel] border-[--border]">
          <DialogHeader>
            <DialogTitle className="text-[--text]">Change Email Address</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                New Email Address
              </label>
              <input
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="your.new.email@example.com"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Current Password (for verification)
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter your current password"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={handleChangeEmail} disabled={submitting} className="flex-1">
                {submitting ? "Updating..." : "Update Email"}
              </Button>
              <Button onClick={() => setChangeEmailModal(false)} variant="outline">
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Password Modal */}
      <Dialog open={changePasswordModal} onOpenChange={setChangePasswordModal}>
        <DialogContent className="bg-[--panel] border-[--border]">
          <DialogHeader>
            <DialogTitle className="text-[--text]">Change Password</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Current Password
              </label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                New Password
              </label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password (min 8 characters)"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Confirm New Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={handleChangePassword} disabled={submitting} className="flex-1">
                {submitting ? "Updating..." : "Update Password"}
              </Button>
              <Button onClick={() => setChangePasswordModal(false)} variant="outline">
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Phone Number Modal */}
      <Dialog open={changePhoneModal} onOpenChange={setChangePhoneModal}>
        <DialogContent className="bg-[--panel] border-[--border]">
          <DialogHeader>
            <DialogTitle className="text-[--text]">Manage Phone Number</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
              <p className="text-sm text-[--primary]">
                Phone number is required for SMS alerts. Format: E.164 (e.g., +14155551234)
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Phone Number
              </label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                placeholder="+14155551234"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border-strong] rounded-lg text-[--text] focus:border-[--primary] focus:outline-none"
              />
              <p className="text-xs text-[--muted] mt-1">
                Include country code (e.g., +1 for US/Canada)
              </p>
            </div>
            <div className="flex gap-3 pt-4">
              <Button onClick={handleChangePhone} disabled={submitting} className="flex-1">
                {submitting ? "Updating..." : "Update Phone Number"}
              </Button>
              <Button onClick={() => setChangePhoneModal(false)} variant="outline">
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Cancel Subscription Modal */}
      <Dialog open={cancelSubscriptionModal} onOpenChange={setCancelSubscriptionModal}>
        <DialogContent className="bg-[--panel] border-[--border]">
          <DialogHeader>
            <DialogTitle className="text-[--text]">Cancel Subscription</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
              <p className="text-sm text-[--warning]">
                Are you sure you want to cancel your subscription? You'll lose access to premium features at the end of your current billing period.
              </p>
            </div>
            <div className="space-y-2 text-sm text-[--muted]">
              <p><strong className="text-[--text]">You'll lose access to:</strong></p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Unlimited alerts and notifications</li>
                <li>Advanced portfolio diagnostics</li>
                <li>Historical event data and backtesting</li>
                <li>Priority customer support</li>
              </ul>
            </div>
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleCancelSubscription}
                disabled={submitting}
                variant="outline"
                className="flex-1 text-[--error] hover:text-[--error] border-red-500/30"
              >
                {submitting ? "Cancelling..." : "Yes, Cancel Subscription"}
              </Button>
              <Button onClick={() => setCancelSubscriptionModal(false)}>
                Keep My Plan
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Scoring Preferences Modal */}
      <ScoringPreferencesModal
        open={scoringModalOpen}
        onClose={() => setScoringModalOpen(false)}
        onSave={() => {
          // Optionally refresh account data after saving preferences
          loadAccountData();
        }}
      />
    </div>
  );
}
