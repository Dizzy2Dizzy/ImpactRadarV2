'use client';

import { useState } from 'react';
import { DashboardTabs } from './DashboardTabs';
import { OnboardingChecklist } from './OnboardingChecklist';
import { api } from '@/lib/api';
import { showToast } from '@/lib/toast';

type Tab = "overview" | "projector" | "events" | "companies" | "watchlist" | "portfolio" | "scanners" | "alerts" | "backtesting" | "correlation" | "calendar" | "radarquant" | "data-quality" | "accuracy" | "admin" | "account" | "xfeed" | "sectors" | "trade-signals" | "settings";

export function DashboardWithOnboarding() {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const handleLoadDemo = async () => {
    try {
      setLoading(true);
      const result = await api.demo.loadDemoData();
      
      if (result.success) {
        showToast(
          `Demo data loaded! Added ${result.portfolio_holdings} portfolio positions, ${result.watchlist_items} watchlist items, and ${result.alerts} alert.`,
          'success'
        );
        
        setTimeout(() => {
          window.location.reload();
        }, 2000);
      }
    } catch (error: any) {
      showToast(error.message || 'Failed to load demo data', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <OnboardingChecklist onLoadDemo={handleLoadDemo} onNavigate={setActiveTab} />
      <DashboardTabs activeTab={activeTab} setActiveTab={setActiveTab} />
    </>
  );
}
