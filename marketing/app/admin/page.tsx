"use client";

import { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { 
  Users, 
  Mail, 
  BarChart3, 
  AlertTriangle, 
  Check, 
  X, 
  Eye,
  Clock,
  Building2,
  Calendar,
  RefreshCw,
  Lock,
  MessageSquare,
  UserCheck,
  Trash2,
  RotateCcw,
  Radar,
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  FileText,
  Plus,
  Edit2,
  Save,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Zap,
  Bug,
  Shield,
  Settings,
  CheckCircle2
} from "lucide-react";

const API_BASE = "/api/proxy";

interface UserStats {
  total_users: number;
  free_users: number;
  pro_users: number;
  team_users: number;
  verified_users: number;
  unverified_users: number;
  users_today: number;
  users_this_week: number;
  users_this_month: number;
}

interface WebsiteStats {
  total_events: number;
  total_companies: number;
  tracked_companies: number;
  events_today: number;
  events_this_week: number;
}

interface ContactMessage {
  id: number;
  name: string;
  email: string;
  message: string;
  status: string;
  created_at: string;
}

interface User {
  id: number;
  email: string;
  phone: string | null;
  plan: string;
  is_verified: boolean;
  is_admin: boolean;
  created_at: string | null;
  last_login: string | null;
}

interface ActiveUser {
  user_id: number;
  email: string | null;
  plan: string | null;
  seconds_ago: number;
}

interface ForumUser {
  id: number;
  email: string | null;
  username: string;
  plan: string;
}

interface ForumMessage {
  id: number;
  user_id: number;
  content: string;
  image_url: string | null;
  is_ai_response: boolean;
  ai_prompt: string | null;
  parent_message_id: number | null;
  created_at: string;
  edited_at: string | null;
  deleted_at: string | null;
  user: ForumUser;
}

interface ScannerInfo {
  key: string;
  label: string;
  interval_minutes: number;
  enabled: boolean;
  use_slow_pool: boolean;
  estimated_duration_seconds: number;
}

interface ScannerResult {
  status: string;
  events_found: number;
  error: string | null;
  completed_at: string | null;
}

interface ScanOperation {
  id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_scanners: number;
  completed_scanners: number;
  scanner_results: Record<string, ScannerResult>;
  estimated_duration_seconds: number;
  total_events_found: number | null;
  error: string | null;
}

interface ChangelogItem {
  id: number;
  category: string;
  description: string;
  icon: string;
  sort_order: number;
}

interface ChangelogRelease {
  id: number;
  version: string;
  title: string;
  release_date: string;
  is_published: boolean;
  items: ChangelogItem[];
}

const ICON_OPTIONS = [
  { value: "Sparkles", label: "Sparkles", icon: Sparkles },
  { value: "Zap", label: "Zap", icon: Zap },
  { value: "Bug", label: "Bug Fix", icon: Bug },
  { value: "Shield", label: "Security", icon: Shield },
  { value: "Settings", label: "Settings", icon: Settings },
  { value: "CheckCircle2", label: "Check", icon: CheckCircle2 },
];

const CATEGORY_OPTIONS = ["New", "Improved", "Fixed", "Security", "API", "Performance", "UI/UX"];

export default function AdminPage() {
  const [adminKey, setAdminKey] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [websiteStats, setWebsiteStats] = useState<WebsiteStats | null>(null);
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [messagesTotal, setMessagesTotal] = useState(0);
  const [messagesUnread, setMessagesUnread] = useState(0);
  const [users, setUsers] = useState<User[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  
  const [activeUsers, setActiveUsers] = useState<ActiveUser[]>([]);
  const [activeUsersCount, setActiveUsersCount] = useState(0);
  
  const [forumMessages, setForumMessages] = useState<ForumMessage[]>([]);
  const [forumMessagesTotal, setForumMessagesTotal] = useState(0);
  const [showDeletedForum, setShowDeletedForum] = useState(false);
  
  const [scanners, setScanners] = useState<ScannerInfo[]>([]);
  const [scanOperation, setScanOperation] = useState<ScanOperation | null>(null);
  const [isTriggeringScan, setIsTriggeringScan] = useState(false);
  
  const [changelogReleases, setChangelogReleases] = useState<ChangelogRelease[]>([]);
  const [isLoadingChangelog, setIsLoadingChangelog] = useState(false);
  const [expandedRelease, setExpandedRelease] = useState<number | null>(null);
  const [editingRelease, setEditingRelease] = useState<number | null>(null);
  const [showNewReleaseForm, setShowNewReleaseForm] = useState(false);
  const [showNewItemForm, setShowNewItemForm] = useState<number | null>(null);
  const [newRelease, setNewRelease] = useState({ version: "", title: "", release_date: new Date().toISOString().split('T')[0] });
  const [newItem, setNewItem] = useState({ category: "New", description: "", icon: "Sparkles" });
  const [editingItem, setEditingItem] = useState<{ id: number; category: string; description: string; icon: string } | null>(null);
  
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'messages' | 'active' | 'forum' | 'scanners' | 'changelog'>('overview');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchWithAuth = async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        ...options.headers,
        "X-Admin-Key": adminKey,
      },
    });
    
    if (response.status === 401) {
      setIsAuthenticated(false);
      throw new Error("Invalid admin key");
    }
    
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "Request failed");
    }
    
    return response.json();
  };

  const verifyAdminKey = async () => {
    if (!adminKey.trim()) {
      setError("Please enter admin key");
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      await fetchWithAuth("/admin/verify");
      setIsAuthenticated(true);
      localStorage.setItem("admin_key", adminKey);
      loadDashboardData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsLoading(false);
    }
  };

  const loadDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const [userStatsRes, websiteStatsRes, messagesRes, usersRes, activeUsersRes, forumRes] = await Promise.all([
        fetchWithAuth("/admin/stats/users"),
        fetchWithAuth("/admin/stats/website"),
        fetchWithAuth("/admin/messages?limit=50"),
        fetchWithAuth("/admin/users/list?limit=100"),
        fetchWithAuth("/admin/active-users"),
        fetchWithAuth(`/admin/forum/messages?limit=50&include_deleted=${showDeletedForum}`),
      ]);
      
      setUserStats(userStatsRes);
      setWebsiteStats(websiteStatsRes);
      setMessages(messagesRes.messages);
      setMessagesTotal(messagesRes.total);
      setMessagesUnread(messagesRes.unread);
      setUsers(usersRes.users);
      setUsersTotal(usersRes.total);
      setActiveUsers(activeUsersRes.users);
      setActiveUsersCount(activeUsersRes.count);
      setForumMessages(forumRes.messages);
      setForumMessagesTotal(forumRes.total);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setIsRefreshing(false);
    }
  };
  
  const loadForumMessages = async () => {
    try {
      const forumRes = await fetchWithAuth(`/admin/forum/messages?limit=50&include_deleted=${showDeletedForum}`);
      setForumMessages(forumRes.messages);
      setForumMessagesTotal(forumRes.total);
    } catch (err) {
      console.error("Failed to load forum messages:", err);
    }
  };

  const deleteForumMessage = async (messageId: number, hardDelete: boolean = false) => {
    try {
      await fetchWithAuth(`/admin/forum/messages/${messageId}?hard_delete=${hardDelete}`, {
        method: "DELETE",
      });
      loadForumMessages();
    } catch (err) {
      console.error("Failed to delete forum message:", err);
    }
  };

  const restoreForumMessage = async (messageId: number) => {
    try {
      await fetchWithAuth(`/admin/forum/messages/${messageId}/restore`, {
        method: "PATCH",
      });
      loadForumMessages();
    } catch (err) {
      console.error("Failed to restore forum message:", err);
    }
  };

  const updateMessageStatus = async (messageId: number, status: string) => {
    try {
      await fetchWithAuth(`/admin/messages/${messageId}?status=${status}`, {
        method: "PATCH",
      });
      loadDashboardData();
    } catch (err) {
      console.error("Failed to update message:", err);
    }
  };

  const loadScannerData = async () => {
    try {
      const [scannersRes, operationRes] = await Promise.all([
        fetchWithAuth("/admin/scanners/list"),
        fetchWithAuth("/admin/scanners/operation-status"),
      ]);
      setScanners(scannersRes.scanners);
      if (operationRes.status !== "idle") {
        setScanOperation(operationRes);
      } else {
        setScanOperation(null);
      }
    } catch (err) {
      console.error("Failed to load scanner data:", err);
    }
  };

  const loadChangelogData = async () => {
    setIsLoadingChangelog(true);
    try {
      const res = await fetchWithAuth("/admin/changelog");
      setChangelogReleases(res.releases);
    } catch (err) {
      console.error("Failed to load changelog:", err);
    } finally {
      setIsLoadingChangelog(false);
    }
  };

  const createRelease = async () => {
    if (!newRelease.version.trim() || !newRelease.title.trim()) return;
    try {
      await fetchWithAuth("/admin/changelog", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version: newRelease.version,
          title: newRelease.title,
          release_date: newRelease.release_date,
          is_published: true,
          items: []
        }),
      });
      setNewRelease({ version: "", title: "", release_date: new Date().toISOString().split('T')[0] });
      setShowNewReleaseForm(false);
      loadChangelogData();
    } catch (err) {
      console.error("Failed to create release:", err);
    }
  };

  const updateRelease = async (releaseId: number, updates: { version?: string; title?: string; release_date?: string; is_published?: boolean }) => {
    try {
      await fetchWithAuth(`/admin/changelog/${releaseId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });
      setEditingRelease(null);
      loadChangelogData();
    } catch (err) {
      console.error("Failed to update release:", err);
    }
  };

  const deleteRelease = async (releaseId: number) => {
    if (!confirm("Are you sure you want to delete this release and all its items?")) return;
    try {
      await fetchWithAuth(`/admin/changelog/${releaseId}`, { method: "DELETE" });
      loadChangelogData();
    } catch (err) {
      console.error("Failed to delete release:", err);
    }
  };

  const addItem = async (releaseId: number) => {
    if (!newItem.description.trim()) return;
    try {
      await fetchWithAuth(`/admin/changelog/${releaseId}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newItem),
      });
      setNewItem({ category: "New", description: "", icon: "Sparkles" });
      setShowNewItemForm(null);
      loadChangelogData();
    } catch (err) {
      console.error("Failed to add item:", err);
    }
  };

  const updateItem = async (itemId: number) => {
    if (!editingItem || !editingItem.description.trim()) return;
    try {
      await fetchWithAuth(`/admin/changelog/items/${itemId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category: editingItem.category,
          description: editingItem.description,
          icon: editingItem.icon,
        }),
      });
      setEditingItem(null);
      loadChangelogData();
    } catch (err) {
      console.error("Failed to update item:", err);
    }
  };

  const deleteItem = async (itemId: number) => {
    if (!confirm("Are you sure you want to delete this item?")) return;
    try {
      await fetchWithAuth(`/admin/changelog/items/${itemId}`, { method: "DELETE" });
      loadChangelogData();
    } catch (err) {
      console.error("Failed to delete item:", err);
    }
  };

  const getIconComponent = (iconName: string) => {
    const iconOption = ICON_OPTIONS.find(opt => opt.value === iconName);
    const IconComponent = iconOption?.icon || CheckCircle2;
    return <IconComponent className="h-4 w-4" />;
  };

  const triggerAllScanners = async () => {
    setIsTriggeringScan(true);
    try {
      const response = await fetchWithAuth("/admin/scanners/trigger-all", {
        method: "POST",
      });
      setScanOperation({
        id: response.operation_id,
        status: "running",
        started_at: new Date().toISOString(),
        completed_at: null,
        total_scanners: response.total_scanners,
        completed_scanners: 0,
        scanner_results: {},
        estimated_duration_seconds: response.estimated_duration_seconds,
        total_events_found: null,
        error: null,
      });
      pollScanStatus();
    } catch (err) {
      console.error("Failed to trigger scanners:", err);
      setError(err instanceof Error ? err.message : "Failed to trigger scanners");
    } finally {
      setIsTriggeringScan(false);
    }
  };

  const pollScanStatus = () => {
    const poll = async () => {
      try {
        const operationRes = await fetchWithAuth("/admin/scanners/operation-status");
        if (operationRes.status !== "idle") {
          setScanOperation(operationRes);
          if (operationRes.status === "running") {
            setTimeout(poll, 3000);
          }
        } else {
          setScanOperation(null);
        }
      } catch (err) {
        console.error("Failed to poll scan status:", err);
      }
    };
    setTimeout(poll, 3000);
  };

  const clearScanOperation = async () => {
    try {
      await fetchWithAuth("/admin/scanners/clear-operation", {
        method: "POST",
      });
      setScanOperation(null);
    } catch (err) {
      console.error("Failed to clear operation:", err);
      setError(err instanceof Error ? err.message : "Failed to clear operation");
    }
  };

  useEffect(() => {
    const savedKey = localStorage.getItem("admin_key");
    if (savedKey) {
      setAdminKey(savedKey);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated && activeTab === 'scanners') {
      loadScannerData();
    }
    if (isAuthenticated && activeTab === 'changelog') {
      loadChangelogData();
    }
  }, [isAuthenticated, activeTab]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString("en-US", {
      timeZone: "America/New_York",
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="py-16 lg:py-24">
          <div className="mx-auto max-w-md px-6">
            <div className="rounded-3xl border border-white/10 bg-[--panel] p-8">
              <div className="flex items-center justify-center mb-6">
                <div className="w-16 h-16 rounded-2xl bg-[--primary]/10 flex items-center justify-center">
                  <Lock className="h-8 w-8 text-[--primary]" />
                </div>
              </div>
              <h1 className="text-2xl font-semibold text-[--text] text-center mb-2">
                Admin Dashboard
              </h1>
              <p className="text-[--muted] text-center mb-6">
                Enter your admin key to access the developer dashboard.
              </p>
              
              {error && (
                <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                  {error}
                </div>
              )}
              
              <div className="space-y-4">
                <input
                  type="password"
                  value={adminKey}
                  onChange={(e) => setAdminKey(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && verifyAdminKey()}
                  placeholder="Enter admin key"
                  className="w-full rounded-lg border border-white/10 bg-[--bg] px-4 py-3 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                />
                <Button 
                  onClick={verifyAdminKey} 
                  className="w-full"
                  disabled={isLoading}
                >
                  {isLoading ? "Verifying..." : "Access Dashboard"}
                </Button>
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="py-8 lg:py-12">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-semibold text-[--text]">
                Admin Dashboard
              </h1>
              <p className="text-[--muted] mt-1">
                Developer monitoring and analytics
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={loadDashboardData}
                disabled={isRefreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  localStorage.removeItem("admin_key");
                  setIsAuthenticated(false);
                  setAdminKey("");
                }}
              >
                Logout
              </Button>
            </div>
          </div>

          <div className="flex gap-2 mb-6 border-b border-white/10 overflow-x-auto">
            {(['overview', 'scanners', 'changelog', 'active', 'users', 'forum', 'messages'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === tab
                    ? 'text-[--primary] border-b-2 border-[--primary]'
                    : 'text-[--muted] hover:text-[--text]'
                }`}
              >
                {tab === 'active' ? 'Active Users' : tab === 'forum' ? 'Forum' : tab === 'scanners' ? 'Scanners' : tab === 'changelog' ? 'Changelog' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                {tab === 'messages' && messagesUnread > 0 && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-[--primary] text-white rounded-full">
                    {messagesUnread}
                  </span>
                )}
                {tab === 'active' && activeUsersCount > 0 && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-green-500 text-white rounded-full">
                    {activeUsersCount}
                  </span>
                )}
                {tab === 'scanners' && scanOperation?.status === 'running' && (
                  <span className="ml-2 px-2 py-0.5 text-xs bg-yellow-500 text-black rounded-full animate-pulse">
                    Running
                  </span>
                )}
              </button>
            ))}
          </div>

          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Total Users"
                  value={userStats?.total_users || 0}
                  icon={<Users className="h-5 w-5" />}
                  color="blue"
                />
                <StatCard
                  title="Total Events"
                  value={websiteStats?.total_events || 0}
                  icon={<BarChart3 className="h-5 w-5" />}
                  color="green"
                />
                <StatCard
                  title="Companies Tracked"
                  value={websiteStats?.tracked_companies || 0}
                  icon={<Building2 className="h-5 w-5" />}
                  color="purple"
                />
                <StatCard
                  title="Unread Messages"
                  value={messagesUnread}
                  icon={<Mail className="h-5 w-5" />}
                  color="orange"
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                  <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                    <Users className="h-5 w-5 text-[--primary]" />
                    User Statistics
                  </h3>
                  <div className="space-y-3">
                    <StatRow label="Free Users" value={userStats?.free_users || 0} />
                    <StatRow label="Pro Users" value={userStats?.pro_users || 0} color="text-blue-400" />
                    <StatRow label="Team Users" value={userStats?.team_users || 0} color="text-purple-400" />
                    <div className="border-t border-white/10 my-3" />
                    <StatRow label="Verified Users" value={userStats?.verified_users || 0} color="text-green-400" />
                    <StatRow label="Unverified Users" value={userStats?.unverified_users || 0} color="text-yellow-400" />
                    <div className="border-t border-white/10 my-3" />
                    <StatRow label="New Today" value={userStats?.users_today || 0} />
                    <StatRow label="This Week" value={userStats?.users_this_week || 0} />
                    <StatRow label="This Month" value={userStats?.users_this_month || 0} />
                  </div>
                </div>

                <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                  <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-[--primary]" />
                    Website Statistics
                  </h3>
                  <div className="space-y-3">
                    <StatRow label="Total Companies" value={websiteStats?.total_companies || 0} />
                    <StatRow label="Tracked Companies" value={websiteStats?.tracked_companies || 0} color="text-green-400" />
                    <div className="border-t border-white/10 my-3" />
                    <StatRow label="Events Today" value={websiteStats?.events_today || 0} />
                    <StatRow label="Events This Week" value={websiteStats?.events_this_week || 0} />
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-400" />
                  Sentry Errors
                </h3>
                <p className="text-[--muted]">
                  View errors directly in your{" "}
                  <a 
                    href="https://sentry.io" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-[--primary] hover:underline"
                  >
                    Sentry Dashboard
                  </a>
                </p>
              </div>
            </div>
          )}

          {activeTab === 'scanners' && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] flex items-center gap-2">
                      <Radar className="h-5 w-5 text-[--primary]" />
                      Scanner Control Center
                    </h3>
                    <p className="text-[--muted] text-sm mt-1">
                      Trigger all 11 event family scanners to update the database with fresh events
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={triggerAllScanners}
                      disabled={isTriggeringScan || scanOperation?.status === 'running'}
                      className="gap-2"
                    >
                      {isTriggeringScan || scanOperation?.status === 'running' ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          {scanOperation?.status === 'running' ? 'Scanning...' : 'Starting...'}
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          Trigger All Scanners
                        </>
                      )}
                    </Button>
                    {scanOperation?.status === 'running' && (
                      <Button
                        onClick={clearScanOperation}
                        variant="outline"
                        className="gap-2 border-red-500/30 text-red-400 hover:bg-red-500/10"
                      >
                        <X className="h-4 w-4" />
                        Clear Operation
                      </Button>
                    )}
                  </div>
                </div>

                {scanOperation && (
                  <div className="mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        {scanOperation.status === 'running' ? (
                          <Loader2 className="h-5 w-5 text-yellow-400 animate-spin" />
                        ) : scanOperation.status === 'completed' ? (
                          <CheckCircle className="h-5 w-5 text-green-400" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-400" />
                        )}
                        <div>
                          <p className="font-medium text-[--text]">
                            {scanOperation.status === 'running' 
                              ? 'Scan in Progress' 
                              : scanOperation.status === 'completed'
                              ? 'Scan Completed'
                              : 'Scan Failed'}
                          </p>
                          <p className="text-xs text-[--muted]">
                            Started: {formatDate(scanOperation.started_at)}
                            {scanOperation.completed_at && ` | Completed: ${formatDate(scanOperation.completed_at)}`}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-[--text]">
                          {scanOperation.completed_scanners} / {scanOperation.total_scanners}
                        </p>
                        <p className="text-xs text-[--muted]">Scanners Complete</p>
                      </div>
                    </div>

                    <div className="w-full bg-white/10 rounded-full h-2 mb-4">
                      <div 
                        className={`h-2 rounded-full transition-all duration-500 ${
                          scanOperation.status === 'completed' ? 'bg-green-500' : 
                          scanOperation.status === 'error' ? 'bg-red-500' : 'bg-[--primary]'
                        }`}
                        style={{ 
                          width: `${(scanOperation.completed_scanners / scanOperation.total_scanners) * 100}%` 
                        }}
                      />
                    </div>

                    {scanOperation.status === 'running' && (
                      <p className="text-sm text-[--muted]">
                        Estimated time remaining: ~{Math.ceil((scanOperation.estimated_duration_seconds * (1 - scanOperation.completed_scanners / scanOperation.total_scanners)) / 60)} minutes
                      </p>
                    )}

                    {scanOperation.status === 'completed' && scanOperation.total_events_found !== null && (
                      <p className="text-sm text-green-400">
                        Total new events found: {scanOperation.total_events_found}
                      </p>
                    )}

                    {scanOperation.error && (
                      <p className="text-sm text-red-400">Error: {scanOperation.error}</p>
                    )}
                  </div>
                )}

                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-[--muted] uppercase tracking-wider">
                    Scanner Status
                  </h4>
                  <div className="grid gap-3">
                    {scanners.map((scanner) => {
                      const result = scanOperation?.scanner_results[scanner.label];
                      return (
                        <div 
                          key={scanner.key}
                          className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-2 h-2 rounded-full ${
                              result?.status === 'success' ? 'bg-green-400' :
                              result?.status === 'error' ? 'bg-red-400' :
                              result?.status === 'running' ? 'bg-yellow-400 animate-pulse' :
                              'bg-white/30'
                            }`} />
                            <div>
                              <p className="font-medium text-[--text]">{scanner.label}</p>
                              <p className="text-xs text-[--muted]">
                                Interval: {scanner.interval_minutes} min
                                {scanner.use_slow_pool && ' (Heavy Scanner)'}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            {result ? (
                              <>
                                <p className={`text-sm font-medium ${
                                  result.status === 'success' ? 'text-green-400' :
                                  result.status === 'error' ? 'text-red-400' :
                                  result.status === 'running' ? 'text-yellow-400' :
                                  'text-[--muted]'
                                }`}>
                                  {result.status === 'success' ? `${result.events_found} events` :
                                   result.status === 'error' ? 'Error' :
                                   result.status === 'running' ? 'Running...' : 'Pending'}
                                </p>
                                {result.error && (
                                  <p className="text-xs text-red-400 max-w-[200px] truncate">
                                    {result.error}
                                  </p>
                                )}
                              </>
                            ) : (
                              <p className="text-sm text-[--muted]">Ready</p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-400" />
                  Admin AI Assistant
                </h3>
                <p className="text-[--muted] mb-4">
                  For comprehensive analysis of Impact Radar, use the RadarQuant AI in the Community Forum. 
                  As an admin, you have full access to all database queries and can ask questions like:
                </p>
                <ul className="list-disc list-inside text-[--muted] space-y-1 text-sm">
                  <li>Show me all events from the last 24 hours</li>
                  <li>Analyze the accuracy of our impact scores</li>
                  <li>What sectors have the most events this week?</li>
                  <li>Generate a report on scanner performance</li>
                </ul>
                <p className="text-[--muted] mt-4 text-sm">
                  Simply mention @Quant in the forum to get AI-powered analysis with full database access.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="rounded-2xl border border-white/10 bg-[--panel] overflow-hidden">
              <div className="p-4 border-b border-white/10">
                <h3 className="text-lg font-semibold text-[--text]">
                  Users ({usersTotal})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-white/5">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">ID</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">Email</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">Plan</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">Joined</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">Last Login</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {users.map((user) => (
                      <tr key={user.id} className="hover:bg-white/5">
                        <td className="px-4 py-3 text-sm text-[--text]">{user.id}</td>
                        <td className="px-4 py-3 text-sm text-[--text]">
                          {user.email || user.phone || "—"}
                          {user.is_admin && (
                            <span className="ml-2 px-2 py-0.5 text-xs bg-[--primary]/20 text-[--primary] rounded">Admin</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 text-xs rounded font-medium ${
                            user.plan === 'pro' 
                              ? 'bg-blue-500/20 text-blue-400'
                              : user.plan === 'team'
                              ? 'bg-purple-500/20 text-purple-400'
                              : 'bg-white/10 text-[--muted]'
                          }`}>
                            {user.plan.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {user.is_verified ? (
                            <span className="flex items-center gap-1 text-green-400 text-sm">
                              <Check className="h-4 w-4" /> Verified
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-yellow-400 text-sm">
                              <Clock className="h-4 w-4" /> Pending
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-[--muted]">
                          {formatDate(user.created_at)}
                        </td>
                        <td className="px-4 py-3 text-sm text-[--muted]">
                          {formatDate(user.last_login)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'messages' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-[--text]">
                  Contact Messages ({messagesTotal})
                </h3>
                <span className="text-sm text-[--muted]">
                  {messagesUnread} unread
                </span>
              </div>
              
              {messages.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-[--panel] p-8 text-center">
                  <Mail className="h-12 w-12 text-[--muted] mx-auto mb-4" />
                  <p className="text-[--muted]">No messages yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {messages.map((msg) => (
                    <div 
                      key={msg.id}
                      className={`rounded-2xl border bg-[--panel] p-6 ${
                        msg.status === 'unread' 
                          ? 'border-[--primary]/30' 
                          : 'border-white/10'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h4 className="font-semibold text-[--text]">{msg.name}</h4>
                          <a 
                            href={`mailto:${msg.email}`}
                            className="text-sm text-[--primary] hover:underline"
                          >
                            {msg.email}
                          </a>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[--muted]">
                            {formatDate(msg.created_at)}
                          </span>
                          {msg.status === 'unread' && (
                            <span className="px-2 py-0.5 text-xs bg-[--primary] text-white rounded">
                              New
                            </span>
                          )}
                        </div>
                      </div>
                      <p className="text-[--text] whitespace-pre-wrap mb-4">{msg.message}</p>
                      <div className="flex gap-2">
                        {msg.status === 'unread' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => updateMessageStatus(msg.id, 'read')}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Mark as Read
                          </Button>
                        ) : msg.status === 'read' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => updateMessageStatus(msg.id, 'archived')}
                          >
                            <Check className="h-4 w-4 mr-1" />
                            Archive
                          </Button>
                        ) : (
                          <span className="text-xs text-[--muted] px-2 py-1 bg-white/5 rounded">
                            Archived
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'active' && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-semibold text-[--text] flex items-center gap-2">
                    <UserCheck className="h-5 w-5 text-green-400" />
                    Active Users ({activeUsersCount})
                  </h3>
                  <span className="text-xs text-[--muted]">
                    Users active in the last 5 minutes
                  </span>
                </div>
                
                {activeUsers.length === 0 ? (
                  <div className="text-center py-8">
                    <Users className="h-12 w-12 text-[--muted] mx-auto mb-4" />
                    <p className="text-[--muted]">No users currently active</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {activeUsers.map((user) => (
                      <div 
                        key={user.user_id}
                        className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                            <Users className="h-5 w-5 text-green-400" />
                          </div>
                          <div>
                            <p className="text-[--text] font-medium">
                              {user.email || `User ${user.user_id}`}
                            </p>
                            <div className="flex items-center gap-2">
                              <span className={`px-2 py-0.5 text-xs rounded font-medium ${
                                user.plan === 'pro' 
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : user.plan === 'team'
                                  ? 'bg-purple-500/20 text-purple-400'
                                  : 'bg-white/10 text-[--muted]'
                              }`}>
                                {(user.plan || 'free').toUpperCase()}
                              </span>
                              <span className="text-xs text-[--muted]">ID: {user.user_id}</span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-1 text-green-400">
                            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                            <span className="text-sm">Online</span>
                          </div>
                          <span className="text-xs text-[--muted]">
                            {user.seconds_ago < 60 
                              ? `${user.seconds_ago}s ago` 
                              : `${Math.floor(user.seconds_ago / 60)}m ago`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'forum' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-[--text] flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-[--primary]" />
                  Community Chat ({forumMessagesTotal})
                </h3>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-sm text-[--muted]">
                    <input
                      type="checkbox"
                      checked={showDeletedForum}
                      onChange={(e) => {
                        setShowDeletedForum(e.target.checked);
                        setTimeout(loadForumMessages, 0);
                      }}
                      className="rounded border-white/20 bg-white/5"
                    />
                    Show deleted
                  </label>
                </div>
              </div>
              
              {forumMessages.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-[--panel] p-8 text-center">
                  <MessageSquare className="h-12 w-12 text-[--muted] mx-auto mb-4" />
                  <p className="text-[--muted]">No forum messages yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {forumMessages.map((msg) => (
                    <div 
                      key={msg.id}
                      className={`rounded-2xl border bg-[--panel] p-5 ${
                        msg.deleted_at 
                          ? 'border-red-500/30 opacity-60' 
                          : msg.is_ai_response
                          ? 'border-purple-500/30'
                          : 'border-white/10'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            msg.is_ai_response 
                              ? 'bg-purple-500/20' 
                              : 'bg-[--primary]/20'
                          }`}>
                            {msg.is_ai_response ? (
                              <span className="text-xs text-purple-400 font-bold">AI</span>
                            ) : (
                              <Users className="h-4 w-4 text-[--primary]" />
                            )}
                          </div>
                          <div>
                            <p className="text-[--text] font-medium">
                              {msg.is_ai_response ? 'Quant AI' : msg.user.username}
                            </p>
                            <div className="flex items-center gap-2">
                              <span className={`px-1.5 py-0.5 text-xs rounded ${
                                msg.user.plan === 'pro' 
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : msg.user.plan === 'team'
                                  ? 'bg-purple-500/20 text-purple-400'
                                  : msg.user.plan === 'ai'
                                  ? 'bg-purple-500/20 text-purple-400'
                                  : 'bg-white/10 text-[--muted]'
                              }`}>
                                {msg.user.plan.toUpperCase()}
                              </span>
                              <span className="text-xs text-[--muted]">
                                {formatDate(msg.created_at)}
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {msg.deleted_at && (
                            <span className="px-2 py-0.5 text-xs bg-red-500/20 text-red-400 rounded">
                              Deleted
                            </span>
                          )}
                          <span className="text-xs text-[--muted]">ID: {msg.id}</span>
                        </div>
                      </div>
                      
                      {msg.content && (
                        <p className="text-[--text] whitespace-pre-wrap mb-3 text-sm">
                          {msg.content}
                        </p>
                      )}
                      
                      {msg.image_url && (
                        <div className="mb-3">
                          <img 
                            src={msg.image_url} 
                            alt="Message attachment" 
                            className="max-h-40 rounded-lg"
                          />
                        </div>
                      )}
                      
                      <div className="flex gap-2 pt-2 border-t border-white/5">
                        {msg.deleted_at ? (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => restoreForumMessage(msg.id)}
                            >
                              <RotateCcw className="h-4 w-4 mr-1" />
                              Restore
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => deleteForumMessage(msg.id, true)}
                              className="text-red-400 hover:text-red-300"
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              Delete Permanently
                            </Button>
                          </>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteForumMessage(msg.id, false)}
                          >
                            <Trash2 className="h-4 w-4 mr-1" />
                            Delete
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'changelog' && (
            <div className="space-y-6">
              <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] flex items-center gap-2">
                      <FileText className="h-5 w-5 text-[--primary]" />
                      Changelog Editor
                    </h3>
                    <p className="text-[--muted] text-sm mt-1">
                      Manage changelog releases displayed on the public changelog page
                    </p>
                  </div>
                  <Button onClick={() => setShowNewReleaseForm(true)} disabled={showNewReleaseForm}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Release
                  </Button>
                </div>

                {showNewReleaseForm && (
                  <div className="mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
                    <h4 className="font-medium text-[--text] mb-4">Create New Release</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      <input
                        type="text"
                        placeholder="Version (e.g., 2.1.0)"
                        value={newRelease.version}
                        onChange={(e) => setNewRelease({ ...newRelease, version: e.target.value })}
                        className="rounded-lg border border-white/10 bg-[--bg] px-3 py-2 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none"
                      />
                      <input
                        type="text"
                        placeholder="Title (e.g., Platform Improvements)"
                        value={newRelease.title}
                        onChange={(e) => setNewRelease({ ...newRelease, title: e.target.value })}
                        className="rounded-lg border border-white/10 bg-[--bg] px-3 py-2 text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none"
                      />
                      <input
                        type="date"
                        value={newRelease.release_date}
                        onChange={(e) => setNewRelease({ ...newRelease, release_date: e.target.value })}
                        className="rounded-lg border border-white/10 bg-[--bg] px-3 py-2 text-[--text] focus:border-[--primary] focus:outline-none"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button onClick={createRelease} size="sm">
                        <Save className="h-4 w-4 mr-1" />
                        Create
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setShowNewReleaseForm(false)}>
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                {isLoadingChangelog ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-[--primary]" />
                  </div>
                ) : changelogReleases.length === 0 ? (
                  <p className="text-[--muted] text-center py-8">No changelog releases yet. Create your first one!</p>
                ) : (
                  <div className="space-y-4">
                    {changelogReleases.map((release) => (
                      <div key={release.id} className="border border-white/10 rounded-xl overflow-hidden">
                        <div 
                          className="flex items-center justify-between p-4 bg-white/5 cursor-pointer hover:bg-white/10 transition-colors"
                          onClick={() => setExpandedRelease(expandedRelease === release.id ? null : release.id)}
                        >
                          <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm bg-[--primary]/20 text-[--primary] px-2 py-1 rounded">
                                v{release.version}
                              </span>
                              {!release.is_published && (
                                <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">Draft</span>
                              )}
                            </div>
                            <div>
                              <p className="font-medium text-[--text]">{release.title}</p>
                              <p className="text-xs text-[--muted]">{release.release_date} - {release.items.length} items</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); updateRelease(release.id, { is_published: !release.is_published }); }}
                            >
                              {release.is_published ? 'Unpublish' : 'Publish'}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => { e.stopPropagation(); deleteRelease(release.id); }}
                              className="text-red-400 hover:text-red-300"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                            {expandedRelease === release.id ? (
                              <ChevronUp className="h-5 w-5 text-[--muted]" />
                            ) : (
                              <ChevronDown className="h-5 w-5 text-[--muted]" />
                            )}
                          </div>
                        </div>
                        
                        {expandedRelease === release.id && (
                          <div className="p-4 border-t border-white/10">
                            <div className="space-y-3">
                              {release.items.map((item) => (
                                <div key={item.id} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg">
                                  {editingItem?.id === item.id ? (
                                    <div className="flex-1 space-y-2">
                                      <div className="flex gap-2">
                                        <select
                                          value={editingItem.icon}
                                          onChange={(e) => setEditingItem({ ...editingItem, icon: e.target.value })}
                                          className="rounded-lg border border-white/10 bg-[--bg] px-2 py-1 text-sm text-[--text]"
                                        >
                                          {ICON_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                          ))}
                                        </select>
                                        <select
                                          value={editingItem.category}
                                          onChange={(e) => setEditingItem({ ...editingItem, category: e.target.value })}
                                          className="rounded-lg border border-white/10 bg-[--bg] px-2 py-1 text-sm text-[--text]"
                                        >
                                          {CATEGORY_OPTIONS.map(cat => (
                                            <option key={cat} value={cat}>{cat}</option>
                                          ))}
                                        </select>
                                      </div>
                                      <input
                                        type="text"
                                        value={editingItem.description}
                                        onChange={(e) => setEditingItem({ ...editingItem, description: e.target.value })}
                                        className="w-full rounded-lg border border-white/10 bg-[--bg] px-3 py-2 text-sm text-[--text] focus:border-[--primary] focus:outline-none"
                                      />
                                      <div className="flex gap-2">
                                        <Button size="sm" onClick={() => updateItem(item.id)}>
                                          <Save className="h-3 w-3 mr-1" />
                                          Save
                                        </Button>
                                        <Button variant="outline" size="sm" onClick={() => setEditingItem(null)}>
                                          Cancel
                                        </Button>
                                      </div>
                                    </div>
                                  ) : (
                                    <>
                                      <div className="w-8 h-8 rounded-lg bg-[--primary]/10 flex items-center justify-center text-[--primary] flex-shrink-0">
                                        {getIconComponent(item.icon)}
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <span className="text-xs font-medium bg-white/10 text-[--muted] px-2 py-0.5 rounded">
                                          {item.category}
                                        </span>
                                        <p className="text-sm text-[--text] mt-1">{item.description}</p>
                                      </div>
                                      <div className="flex gap-1 flex-shrink-0">
                                        <button
                                          onClick={() => setEditingItem({ id: item.id, category: item.category, description: item.description, icon: item.icon })}
                                          className="p-1.5 rounded hover:bg-white/10 text-[--muted] hover:text-[--text]"
                                        >
                                          <Edit2 className="h-4 w-4" />
                                        </button>
                                        <button
                                          onClick={() => deleteItem(item.id)}
                                          className="p-1.5 rounded hover:bg-red-500/10 text-[--muted] hover:text-red-400"
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </button>
                                      </div>
                                    </>
                                  )}
                                </div>
                              ))}
                            </div>
                            
                            {showNewItemForm === release.id ? (
                              <div className="mt-4 p-4 bg-white/5 rounded-lg border border-white/10">
                                <div className="flex gap-2 mb-3">
                                  <select
                                    value={newItem.icon}
                                    onChange={(e) => setNewItem({ ...newItem, icon: e.target.value })}
                                    className="rounded-lg border border-white/10 bg-[--bg] px-2 py-1 text-sm text-[--text]"
                                  >
                                    {ICON_OPTIONS.map(opt => (
                                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                  </select>
                                  <select
                                    value={newItem.category}
                                    onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
                                    className="rounded-lg border border-white/10 bg-[--bg] px-2 py-1 text-sm text-[--text]"
                                  >
                                    {CATEGORY_OPTIONS.map(cat => (
                                      <option key={cat} value={cat}>{cat}</option>
                                    ))}
                                  </select>
                                </div>
                                <input
                                  type="text"
                                  placeholder="Description"
                                  value={newItem.description}
                                  onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                                  className="w-full rounded-lg border border-white/10 bg-[--bg] px-3 py-2 text-sm text-[--text] placeholder:text-[--muted] focus:border-[--primary] focus:outline-none mb-3"
                                />
                                <div className="flex gap-2">
                                  <Button size="sm" onClick={() => addItem(release.id)}>
                                    <Plus className="h-3 w-3 mr-1" />
                                    Add Item
                                  </Button>
                                  <Button variant="outline" size="sm" onClick={() => setShowNewItemForm(null)}>
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <Button 
                                variant="outline" 
                                size="sm" 
                                className="mt-4"
                                onClick={() => setShowNewItemForm(release.id)}
                              >
                                <Plus className="h-4 w-4 mr-1" />
                                Add Item
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}

function StatCard({ 
  title, 
  value, 
  icon, 
  color 
}: { 
  title: string; 
  value: number; 
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'purple' | 'orange';
}) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    purple: 'bg-purple-500/10 text-purple-400',
    orange: 'bg-orange-500/10 text-orange-400',
  };

  return (
    <div className="rounded-2xl border border-white/10 bg-[--panel] p-6">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${colorClasses[color]}`}>
          {icon}
        </div>
        <span className="text-sm text-[--muted]">{title}</span>
      </div>
      <p className="text-3xl font-semibold text-[--text]">
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function StatRow({ 
  label, 
  value, 
  color = 'text-[--text]' 
}: { 
  label: string; 
  value: number;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[--muted]">{label}</span>
      <span className={`font-medium ${color}`}>{value.toLocaleString()}</span>
    </div>
  );
}
