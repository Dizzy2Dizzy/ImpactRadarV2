"use client";

import { OverviewTab } from "./OverviewTab";
import { PortfolioTab } from "./PortfolioTab";
import { WatchlistTab } from "./WatchlistTab";
import { EventsTab } from "./EventsTab";
import { CompaniesTab } from "./CompaniesTab";
import { ScannersTab } from "./ScannersTab";
import { AlertsTab } from "./AlertsTab";
import { AccountTab } from "./AccountTab";
import { RadarQuantTab } from "./RadarQuantTab";
import { BacktestingTab } from "./BacktestingTab";
import { CorrelationTab } from "./CorrelationTab";
import { CalendarTab } from "./CalendarTab";
import { ProjectorTab } from "./ProjectorTab";
import { XFeedTab } from "./XFeedTab";
import { SectorsTab } from "./SectorsTab";
import { TradeSignalsTab } from "./TradeSignalsTab";
import { SettingsTab } from "./SettingsTab";
import { ForumTab } from "./ForumTab";
import { ModelingTab } from "./ModelingTab";
import { PlaybooksTab } from "./PlaybooksTab";
import DataQualityPage from "../../app/dashboard/data-quality/page";
import AdminPage from "../../app/dashboard/admin/page";
import AccuracyPage from "../../app/dashboard/accuracy/page";
import { useState, useEffect, ReactNode, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

type Tab = "overview" | "projector" | "events" | "companies" | "watchlist" | "portfolio" | "scanners" | "alerts" | "backtesting" | "correlation" | "calendar" | "radarquant" | "data-quality" | "accuracy" | "admin" | "account" | "xfeed" | "sectors" | "trade-signals" | "settings" | "forum" | "modeling" | "playbooks";

const Icons = {
  overview: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  projector: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v4" />
      <path d="M12 18v4" />
      <path d="m4.93 4.93 2.83 2.83" />
      <path d="m16.24 16.24 2.83 2.83" />
      <path d="M2 12h4" />
      <path d="M18 12h4" />
      <path d="m4.93 19.07 2.83-2.83" />
      <path d="m16.24 7.76 2.83-2.83" />
    </svg>
  ),
  events: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2Zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2" />
      <path d="M18 14h-8" />
      <path d="M15 18h-5" />
      <path d="M10 6h8v4h-8V6Z" />
    </svg>
  ),
  calendar: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4" />
      <path d="M8 2v4" />
      <path d="M3 10h18" />
      <path d="M8 14h.01" />
      <path d="M12 14h.01" />
      <path d="M16 14h.01" />
      <path d="M8 18h.01" />
      <path d="M12 18h.01" />
    </svg>
  ),
  companies: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="2" />
      <path d="M9 22v-4h6v4" />
      <path d="M8 6h.01" />
      <path d="M16 6h.01" />
      <path d="M12 6h.01" />
      <path d="M12 10h.01" />
      <path d="M12 14h.01" />
      <path d="M16 10h.01" />
      <path d="M16 14h.01" />
      <path d="M8 10h.01" />
      <path d="M8 14h.01" />
    </svg>
  ),
  sectors: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m3 17 6-6 4 4 8-8" />
      <path d="M17 7h4v4" />
    </svg>
  ),
  watchlist: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  ),
  portfolio: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
  tradeSignals: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  ),
  alerts: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  ),
  scanners: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
      <path d="M7 12h10" />
    </svg>
  ),
  correlation: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14" />
      <path d="m19 12-7 7-7-7" />
      <path d="M5 12h14" />
    </svg>
  ),
  backtesting: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l4 2" />
    </svg>
  ),
  dataQuality: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M3 5v14a9 3 0 0 0 18 0V5" />
      <path d="M3 12a9 3 0 0 0 18 0" />
    </svg>
  ),
  accuracy: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  ),
  radarquant: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 8V4H8" />
      <rect x="8" y="8" width="8" height="8" rx="2" />
      <path d="M12 20v-4h4" />
      <path d="M20 12h-4v-4" />
      <path d="M4 12h4v4" />
    </svg>
  ),
  xfeed: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  admin: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  account: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="5" />
      <path d="M20 21a8 8 0 0 0-16 0" />
    </svg>
  ),
  settings: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ),
  forum: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      <path d="M8 10h.01" />
      <path d="M12 10h.01" />
      <path d="M16 10h.01" />
    </svg>
  ),
  radar: (color: string) => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19.07 4.93A10 10 0 0 0 6.99 3.34" />
      <path d="M4 6h.01" />
      <path d="M2.29 9.62A10 10 0 1 0 21.31 8.35" />
      <path d="M16.24 7.76A6 6 0 1 0 8.23 16.67" />
      <path d="M12 18h.01" />
      <path d="M17.99 11.66A6 6 0 0 1 15.77 16.67" />
      <circle cx="12" cy="12" r="2" />
      <path d="m13.41 10.59 5.66-5.66" />
    </svg>
  ),
  pulse: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  ),
  modeling: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  ),
  playbooks: (color: string) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <path d="M8 7h8" />
      <path d="M8 11h8" />
      <path d="M8 15h5" />
    </svg>
  ),
};

interface TabItem {
  id: Tab;
  label: string;
  iconKey: keyof typeof Icons;
  section: string;
  color: string;
}

interface DashboardTabsProps {
  activeTab: Tab;
  setActiveTab: (tab: Tab) => void;
}

export function DashboardTabs({ activeTab, setActiveTab }: DashboardTabsProps) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [userEmail, setUserEmail] = useState<string>("");
  const [userPlan, setUserPlan] = useState<string>("");
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileUsername, setProfileUsername] = useState<string>("");
  const [profilePicturePreview, setProfilePicturePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const response = await fetch("/api/proxy/account/summary");
        if (response.ok) {
          const data = await response.json();
          const adminEmails = ["admin@impactradar.com", "admin@releaseradar.com"];
          setIsAdmin(
            adminEmails.includes(data.email?.toLowerCase()) || 
            data.plan?.toLowerCase() === "admin" ||
            data.is_admin === true
          );
          setUserEmail(data.email || "User");
          setUserPlan(data.plan || "Member");
          setProfileUsername(data.username || data.email?.split('@')[0] || "");
          if (data.avatar_url) {
            setProfilePicturePreview(data.avatar_url);
          }
        }
      } catch (error) {
        console.error("Error checking admin status:", error);
      }
    };
    checkAdminStatus();
  }, []);

  const handleProfilePictureChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setProfilePicturePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSaveProfile = async () => {
    try {
      const payload: { username?: string; avatar_url?: string } = {};
      
      if (profileUsername) {
        payload.username = profileUsername;
      }
      
      if (profilePicturePreview) {
        payload.avatar_url = profilePicturePreview;
      }
      
      const response = await fetch("/api/proxy/auth/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        setProfileUsername(data.username || "");
        if (data.avatar_url) {
          setProfilePicturePreview(data.avatar_url);
        }
        setUserEmail(data.email || userEmail);
        setShowProfileModal(false);
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error("Failed to save profile:", errorData);
        alert("Failed to save profile. Please try again.");
      }
    } catch (error) {
      console.error("Error saving profile:", error);
      alert("Error saving profile. Please try again.");
    }
  };

  const capitalizeFirstLetter = (str: string) => {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
  };

  const tabs: TabItem[] = [
    { id: "overview", label: "Overview", iconKey: "overview", section: "Dashboard", color: "#3b82f6" },
    { id: "projector", label: "Projector", iconKey: "projector", section: "Dashboard", color: "#a855f7" },
    { id: "events", label: "Events", iconKey: "events", section: "Market Data", color: "#f59e0b" },
    { id: "calendar", label: "Calendar", iconKey: "calendar", section: "Market Data", color: "#6366f1" },
    { id: "companies", label: "Companies", iconKey: "companies", section: "Market Data", color: "#64748b" },
    { id: "sectors", label: "Sectors", iconKey: "sectors", section: "Market Data", color: "#22c55e" },
    { id: "watchlist", label: "Watchlist", iconKey: "watchlist", section: "Personal", color: "#eab308" },
    { id: "portfolio", label: "Portfolio", iconKey: "portfolio", section: "Personal", color: "#06b6d4" },
    { id: "trade-signals", label: "Trade Signals", iconKey: "tradeSignals", section: "Trading", color: "#ef4444" },
    { id: "playbooks", label: "Playbooks", iconKey: "playbooks", section: "Trading", color: "#6366f1" },
    { id: "alerts", label: "Alerts", iconKey: "alerts", section: "Trading", color: "#f97316" },
    { id: "scanners", label: "Scanner Status", iconKey: "scanners", section: "System", color: "#8b5cf6" },
    { id: "forum", label: "Community", iconKey: "forum", section: "System", color: "#10b981" },
    { id: "correlation", label: "Correlation", iconKey: "correlation", section: "Analytics", color: "#ec4899" },
    { id: "backtesting", label: "Backtesting", iconKey: "backtesting", section: "Analytics", color: "#14b8a6" },
    { id: "modeling", label: "Modeling", iconKey: "modeling", section: "Analytics", color: "#8b5cf6" },
    { id: "data-quality", label: "Data Quality", iconKey: "dataQuality", section: "Analytics", color: "#a855f7" },
    { id: "accuracy", label: "Accuracy", iconKey: "accuracy", section: "Analytics", color: "#22c55e" },
    { id: "radarquant", label: "RadarQuant AI", iconKey: "radarquant", section: "AI", color: "#3b82f6" },
    { id: "xfeed", label: "X Sentiment", iconKey: "xfeed", section: "AI", color: "#0ea5e9" },
    ...(isAdmin ? [{ id: "admin" as Tab, label: "Admin", iconKey: "admin" as keyof typeof Icons, section: "System", color: "#64748b" }] : []),
    { id: "account", label: "Account", iconKey: "account", section: "Settings", color: "#3b82f6" },
    { id: "settings", label: "Settings", iconKey: "settings", section: "Settings", color: "#64748b" },
  ];

  const sections = tabs.reduce((acc, tab) => {
    if (!acc[tab.section]) {
      acc[tab.section] = [];
    }
    acc[tab.section].push(tab);
    return acc;
  }, {} as Record<string, TabItem[]>);

  const currentTab = tabs.find(t => t.id === activeTab);

  const handleTabClick = (tabId: Tab) => {
    setActiveTab(tabId);
    setSidebarOpen(false);
  };

  return (
    <div className="flex min-h-[calc(100vh-200px)]">
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      <nav
        className={`
          fixed lg:static
          top-0 left-0 h-screen lg:h-auto
          ${sidebarCollapsed ? 'w-[72px] min-w-[72px]' : 'w-[280px] min-w-[280px]'}
          bg-gradient-to-b from-[#1e222d] to-[#131722]
          border-r border-[--border]
          z-50 lg:z-auto
          flex-col
          shadow-2xl lg:shadow-none
          transition-all duration-300 ease-in-out
          ${sidebarOpen ? 'flex translate-x-0' : '-translate-x-full lg:translate-x-0'}
          lg:flex
        `}
      >
        <div className={`p-5 border-b border-[--border] flex items-center ${sidebarCollapsed ? 'justify-center' : 'justify-between'}`}>
          <div className={`flex items-center ${sidebarCollapsed ? '' : 'gap-3'}`}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 flex-shrink-0">
              {Icons.radar("#ffffff")}
            </div>
            {!sidebarCollapsed && (
              <div>
                <div className="font-bold text-[--text]">Impact Radar</div>
                <div className="text-xs text-[--muted]">Event Signal Engine</div>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden w-8 h-8 rounded-lg hover:bg-[--surface-hover] flex items-center justify-center text-[--muted] hover:text-[--text] transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>

        <div className={`flex-1 overflow-y-auto py-4 ${sidebarCollapsed ? 'px-2' : 'px-3'} space-y-6`}>
          {Object.entries(sections).map(([sectionName, sectionTabs]) => (
            <div key={sectionName}>
              {!sidebarCollapsed && (
                <div className="px-3 mb-2 text-[10px] font-semibold text-[--muted] uppercase tracking-wider">
                  {sectionName}
                </div>
              )}
              <div className="space-y-1">
                {sectionTabs.map((tab) => {
                  const isActive = activeTab === tab.id;
                  const iconColor = isActive ? tab.color : "#787b86";
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      title={sidebarCollapsed ? tab.label : undefined}
                      className={`
                        w-full flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'} ${sidebarCollapsed ? 'px-2' : 'px-3'} py-2.5 rounded-lg
                        text-sm font-medium transition-all duration-200
                        ${isActive 
                          ? `bg-gradient-to-r from-[--primary-soft] to-[--primary-light] text-[--primary] ${sidebarCollapsed ? '' : 'border-l-[3px] border-[--primary] pl-[9px]'}` 
                          : 'text-[--muted] hover:text-[--text] hover:bg-[--surface-muted] hover:translate-x-1'
                        }
                      `}
                    >
                      <span className="flex-shrink-0">{Icons[tab.iconKey](iconColor)}</span>
                      {!sidebarCollapsed && <span>{tab.label}</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className={`${sidebarCollapsed ? 'p-2' : 'p-4'} border-t border-[--border] space-y-3`}>
          {/* Collapse Toggle Button - Desktop Only */}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="hidden lg:flex w-full items-center justify-center gap-2 p-2 rounded-lg hover:bg-[--surface-muted] text-[--muted] hover:text-[--text] transition-colors"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <svg 
              width="18" 
              height="18" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2" 
              strokeLinecap="round" 
              strokeLinejoin="round"
              className={`transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`}
            >
              <path d="M11 17l-5-5 5-5" />
              <path d="M18 17l-5-5 5-5" />
            </svg>
            {!sidebarCollapsed && <span className="text-sm">Collapse</span>}
          </button>

          {/* User Profile */}
          <div 
            className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3'} ${sidebarCollapsed ? 'p-2' : 'p-3'} rounded-xl bg-[--surface-muted] cursor-pointer hover:bg-[--surface-hover] transition-colors`}
            onClick={() => setShowProfileModal(true)}
            title={sidebarCollapsed ? (profileUsername || userEmail) : undefined}
          >
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 overflow-hidden flex-shrink-0">
              {profilePicturePreview ? (
                <img src={profilePicturePreview} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                Icons.account("#ffffff")
              )}
            </div>
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[--text] truncate" title={profileUsername || userEmail}>
                  {profileUsername || userEmail || "User"}
                </div>
                <div className="text-xs text-[--muted]">
                  {isAdmin ? 'Admin' : capitalizeFirstLetter(userPlan) || 'Member'}
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      <Dialog open={showProfileModal} onOpenChange={setShowProfileModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Profile</DialogTitle>
            <DialogDescription>
              Update your profile picture and display name.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            <div className="flex flex-col items-center gap-4">
              <div 
                className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
                onClick={() => fileInputRef.current?.click()}
              >
                {profilePicturePreview ? (
                  <img src={profilePicturePreview} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="8" r="5" />
                    <path d="M20 21a8 8 0 0 0-16 0" />
                  </svg>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleProfilePictureChange}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-sm text-[--primary] hover:opacity-80 transition-colors"
              >
                Change Photo
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-[--text]">
                Username
              </label>
              <input
                type="text"
                value={profileUsername}
                onChange={(e) => setProfileUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full px-4 py-2.5 rounded-lg bg-[--surface-muted] border border-[--border] text-[--text] placeholder-[--muted] focus:outline-none focus:border-[--border-strong] transition-colors"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-[--text]">
                Email
              </label>
              <input
                type="email"
                value={userEmail}
                disabled
                className="w-full px-4 py-2.5 rounded-lg bg-[--surface] border border-[--border-muted] text-[--muted] cursor-not-allowed"
              />
              <p className="text-xs text-[--muted]">Email cannot be changed here.</p>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setShowProfileModal(false)}
                className="flex-1 px-4 py-2.5 rounded-lg border border-[--border] text-[--text] hover:bg-[--surface-muted] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveProfile}
                className="flex-1 px-4 py-2.5 rounded-lg bg-blue-500 text-white hover:bg-blue-600 transition-colors font-medium"
              >
                Save Changes
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <div className="flex-1 min-w-0">
        <div className="sticky top-0 z-30 bg-[--panel] backdrop-blur-sm border-b border-[--border] px-4 py-3 flex items-center gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden w-10 h-10 rounded-xl bg-[--surface-muted] border border-[--border] flex items-center justify-center text-[--text] hover:bg-[--surface-hover] hover:border-[--border-strong] transition-all duration-200 shadow-lg"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          
          <div className="flex items-center gap-3">
            {currentTab && (
              <span className="flex-shrink-0">{Icons[currentTab.iconKey](currentTab.color)}</span>
            )}
            <h1 className="text-xl font-bold text-[--text]">{currentTab?.label}</h1>
          </div>
        </div>

        <div className="p-4 lg:p-6 h-full">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {activeTab === "overview" && <OverviewTab onNavigate={(tab) => setActiveTab(tab as Tab)} />}
              {activeTab === "projector" && <ProjectorTab />}
              {activeTab === "events" && <EventsTab />}
              {activeTab === "calendar" && <CalendarTab />}
              {activeTab === "companies" && <CompaniesTab />}
              {activeTab === "watchlist" && <WatchlistTab />}
              {activeTab === "portfolio" && <PortfolioTab />}
              {activeTab === "sectors" && <SectorsTab />}
              {activeTab === "trade-signals" && <TradeSignalsTab />}
              {activeTab === "scanners" && <ScannersTab />}
              {activeTab === "alerts" && <AlertsTab />}
              {activeTab === "correlation" && <CorrelationTab />}
              {activeTab === "backtesting" && <BacktestingTab />}
              {activeTab === "modeling" && <ModelingTab />}
              {activeTab === "data-quality" && <DataQualityPage />}
              {activeTab === "accuracy" && <AccuracyPage />}
              {activeTab === "radarquant" && <RadarQuantTab />}
              {activeTab === "admin" && isAdmin && <AdminPage />}
              {activeTab === "account" && <AccountTab />}
              {activeTab === "settings" && <SettingsTab />}
              {activeTab === "xfeed" && <XFeedTab />}
              {activeTab === "forum" && <ForumTab />}
              {activeTab === "playbooks" && <PlaybooksTab />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
