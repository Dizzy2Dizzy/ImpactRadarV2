'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Sliders, RotateCcw, TrendingUp, Building2, Filter } from 'lucide-react';

interface ScoringPreferences {
  event_type_weights: Record<string, number>;
  sector_weights: Record<string, number>;
  confidence_threshold: number;
  min_impact_score: number;
}

interface ScoringPreferencesModalProps {
  open: boolean;
  onClose: () => void;
  onSave?: () => void;
}

const EVENT_TYPES = [
  { key: 'fda_approval', label: 'FDA Approval' },
  { key: 'fda_rejection', label: 'FDA Rejection' },
  { key: 'sec_8k', label: 'SEC 8-K Filings' },
  { key: 'sec_10q', label: 'SEC 10-Q Filings' },
  { key: 'earnings', label: 'Earnings Reports' },
  { key: 'merger_acquisition', label: 'M&A Activity' },
  { key: 'product_launch', label: 'Product Launches' },
  { key: 'guidance_raise', label: 'Guidance Raise' },
  { key: 'guidance_lower', label: 'Guidance Lower' },
];

const SECTORS = [
  { key: 'Healthcare', label: 'Healthcare' },
  { key: 'Technology', label: 'Technology' },
  { key: 'Finance', label: 'Finance' },
  { key: 'Energy', label: 'Energy' },
  { key: 'Consumer', label: 'Consumer' },
  { key: 'Industrials', label: 'Industrials' },
];

export function ScoringPreferencesModal({
  open,
  onClose,
  onSave,
}: ScoringPreferencesModalProps) {
  const [preferences, setPreferences] = useState<ScoringPreferences>({
    event_type_weights: {},
    sector_weights: {},
    confidence_threshold: 0.5,
    min_impact_score: 0,
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isDefault, setIsDefault] = useState(true);

  useEffect(() => {
    if (open) {
      loadPreferences();
    }
  }, [open]);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/proxy/preferences/scoring');
      if (res.ok) {
        const data = await res.json();
        setPreferences(data.preferences);
        setIsDefault(data.is_default);
      }
    } catch (err) {
      console.error('Failed to load preferences:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      const res = await fetch('/api/proxy/preferences/scoring', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });

      if (res.ok) {
        const data = await res.json();
        setIsDefault(data.is_default);
        onSave?.();
        onClose();
      } else {
        const error = await res.json();
        alert(`Failed to save preferences: ${error.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to save preferences:', err);
      alert('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset all scoring preferences to defaults?')) {
      return;
    }

    try {
      setSaving(true);
      const res = await fetch('/api/proxy/preferences/scoring/reset', {
        method: 'POST',
      });

      if (res.ok) {
        const data = await res.json();
        setPreferences(data.preferences);
        setIsDefault(data.is_default);
        onSave?.();
      }
    } catch (err) {
      console.error('Failed to reset preferences:', err);
      alert('Failed to reset preferences');
    } finally {
      setSaving(false);
    }
  };

  const updateEventTypeWeight = (eventType: string, weight: number) => {
    setPreferences(prev => ({
      ...prev,
      event_type_weights: {
        ...prev.event_type_weights,
        [eventType]: weight,
      },
    }));
  };

  const updateSectorWeight = (sector: string, weight: number) => {
    setPreferences(prev => ({
      ...prev,
      sector_weights: {
        ...prev.sector_weights,
        [sector]: weight,
      },
    }));
  };

  const getWeightLabel = (weight: number | undefined) => {
    if (!weight || weight === 1.0) return 'Default (1.0x)';
    return `${weight.toFixed(1)}x`;
  };

  const getWeightColor = (weight: number | undefined) => {
    if (!weight || weight === 1.0) return 'text-gray-400';
    if (weight > 1.0) return 'text-green-400';
    return 'text-orange-400';
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-[--panel] border-white/10">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold text-[--text] flex items-center gap-2">
            <Sliders className="h-6 w-6" />
            Customize Scoring Preferences
          </DialogTitle>
          <DialogDescription className="text-[--muted]">
            Adjust event impact scoring based on your trading strategy and risk preferences.
            Changes apply to all future event displays.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
          </div>
        ) : (
          <div className="space-y-6 py-4">
            {/* Event Type Weights */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-blue-400" />
                <h3 className="text-lg font-semibold text-[--text]">Event Type Weights</h3>
              </div>
              <p className="text-sm text-[--muted]">
                Adjust the importance of different event types. Higher weights (1.5x-2.0x) increase impact scores,
                lower weights (0.5x-0.9x) decrease them.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                {EVENT_TYPES.map(({ key, label }) => {
                  const weight = preferences.event_type_weights[key] || 1.0;
                  return (
                    <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-[--text]">{label}</span>
                        <span className={`text-sm font-bold ${getWeightColor(weight)}`}>
                          {getWeightLabel(weight)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.5"
                        max="2.0"
                        step="0.1"
                        value={weight}
                        onChange={(e) => updateEventTypeWeight(key, parseFloat(e.target.value))}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[--primary]"
                      />
                      <div className="flex justify-between text-xs text-[--muted] mt-1">
                        <span>0.5x</span>
                        <span>1.0x</span>
                        <span>2.0x</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sector Weights */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-[--text]">Sector Weights</h3>
              </div>
              <p className="text-sm text-[--muted]">
                Adjust the importance of events by company sector based on your portfolio focus.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                {SECTORS.map(({ key, label }) => {
                  const weight = preferences.sector_weights[key] || 1.0;
                  return (
                    <div key={key} className="rounded-lg border border-white/10 bg-black/20 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-[--text]">{label}</span>
                        <span className={`text-sm font-bold ${getWeightColor(weight)}`}>
                          {getWeightLabel(weight)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0.5"
                        max="2.0"
                        step="0.1"
                        value={weight}
                        onChange={(e) => updateSectorWeight(key, parseFloat(e.target.value))}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[--primary]"
                      />
                      <div className="flex justify-between text-xs text-[--muted] mt-1">
                        <span>0.5x</span>
                        <span>1.0x</span>
                        <span>2.0x</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Filters */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Filter className="h-5 w-5 text-green-400" />
                <h3 className="text-lg font-semibold text-[--text]">Filters</h3>
              </div>
              <p className="text-sm text-[--muted]">
                Set minimum thresholds to filter out low-confidence or low-impact events.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[--text]">Minimum Confidence</span>
                    <span className="text-sm font-bold text-blue-400">
                      {(preferences.confidence_threshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={preferences.confidence_threshold}
                    onChange={(e) =>
                      setPreferences(prev => ({
                        ...prev,
                        confidence_threshold: parseFloat(e.target.value),
                      }))
                    }
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[--primary]"
                  />
                  <div className="flex justify-between text-xs text-[--muted] mt-1">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-[--text]">Minimum Impact Score</span>
                    <span className="text-sm font-bold text-green-400">
                      {preferences.min_impact_score}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={preferences.min_impact_score}
                    onChange={(e) =>
                      setPreferences(prev => ({
                        ...prev,
                        min_impact_score: parseInt(e.target.value),
                      }))
                    }
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[--primary]"
                  />
                  <div className="flex justify-between text-xs text-[--muted] mt-1">
                    <span>0</span>
                    <span>50</span>
                    <span>100</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Info */}
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-4">
              <div className="flex items-start gap-3">
                <div className="text-blue-400 mt-0.5">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="font-medium text-blue-400 mb-1">How it works</h4>
                  <ul className="text-sm text-blue-300 space-y-1">
                    <li>• Weights multiply the base impact score (e.g., 1.5x makes a 60 score into 90)</li>
                    <li>• Both event type and sector weights apply cumulatively</li>
                    <li>• Scores are clamped to 0-100 range after adjustment</li>
                    <li>• Filters hide events below the thresholds completely</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="flex items-center justify-between gap-3">
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={saving || isDefault}
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            Reset to Defaults
          </Button>

          <div className="flex items-center gap-3">
            <Button variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving || loading}>
              {saving ? 'Saving...' : 'Save Preferences'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
