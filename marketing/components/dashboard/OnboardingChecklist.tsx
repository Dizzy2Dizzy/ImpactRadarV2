'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, Circle, X } from 'lucide-react';

type Tab = "overview" | "events" | "companies" | "watchlist" | "portfolio" | "scanners" | "alerts" | "radarquant" | "account";

interface ChecklistItem {
  id: string;
  label: string;
  completed: boolean;
  targetTab: Tab;
}

interface OnboardingChecklistProps {
  onLoadDemo: () => void;
  onNavigate: (tab: Tab) => void;
  onRefresh?: () => void;
}

export function OnboardingChecklist({ onLoadDemo, onNavigate, onRefresh }: OnboardingChecklistProps) {
  const [items, setItems] = useState<ChecklistItem[]>([
    {
      id: 'portfolio',
      label: 'Upload your portfolio',
      completed: false,
      targetTab: 'portfolio',
    },
    {
      id: 'watchlist',
      label: 'Add tickers to watchlist',
      completed: false,
      targetTab: 'watchlist',
    },
    {
      id: 'alert',
      label: 'Create your first alert',
      completed: false,
      targetTab: 'alerts',
    }
  ]);
  const [loading, setLoading] = useState(true);
  const [isDismissed, setIsDismissed] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem('onboarding-dismissed');
    if (dismissed === 'true') {
      setIsDismissed(true);
    }
    checkCompletion();
  }, []);

  const checkCompletion = async () => {
    try {
      setLoading(true);
      
      const [portfolioRes, watchlistRes, alertsRes] = await Promise.all([
        fetch('/api/proxy/portfolio').then(r => r.ok ? r.json() : null),
        fetch('/api/proxy/watchlist').then(r => r.ok ? r.json() : null),
        fetch('/api/proxy/alerts').then(r => r.ok ? r.json() : null),
      ]);

      const hasPortfolio = portfolioRes?.positions && portfolioRes.positions.length > 0;
      const hasWatchlist = Array.isArray(watchlistRes) && watchlistRes.length > 0;
      const hasAlerts = Array.isArray(alertsRes) && alertsRes.length > 0;

      setItems(prev => prev.map(item => {
        if (item.id === 'portfolio') return { ...item, completed: hasPortfolio };
        if (item.id === 'watchlist') return { ...item, completed: hasWatchlist };
        if (item.id === 'alert') return { ...item, completed: hasAlerts };
        return item;
      }));
    } catch (error) {
      console.error('Failed to check completion status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('onboarding-dismissed', 'true');
    setIsDismissed(true);
  };

  const handleItemClick = (item: ChecklistItem) => {
    if (!item.completed) {
      onNavigate(item.targetTab);
    }
  };

  const allCompleted = items.every(item => item.completed);
  
  if (loading || allCompleted || isDismissed) {
    return null;
  }

  return (
    <div className="bg-blue-600/10 border border-blue-500/30 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[--text]">
          Welcome to Impact Radar! Get started:
        </h3>
        <div className="flex items-center gap-3">
          <button
            onClick={onLoadDemo}
            className="text-xs text-blue-400 hover:text-blue-300 hover:underline transition-colors"
          >
            or load demo data →
          </button>
          <button
            onClick={handleDismiss}
            className="text-[--muted] hover:text-[--text] transition-colors p-1 hover:bg-white/5 rounded"
            aria-label="Dismiss onboarding"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <div className="space-y-2">
        {items.map(item => (
          <button
            key={item.id}
            onClick={() => handleItemClick(item)}
            disabled={item.completed}
            className={`
              flex items-center gap-2 p-2 rounded w-full text-left transition-all
              ${item.completed ? 'cursor-default' : 'cursor-pointer hover:bg-blue-500/5'}
            `}
          >
            {item.completed ? (
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
            ) : (
              <Circle className="w-5 h-5 text-[--muted] flex-shrink-0" />
            )}
            <span className={`text-sm ${item.completed ? 'text-[--muted] line-through' : 'text-[--text]'}`}>
              {item.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
