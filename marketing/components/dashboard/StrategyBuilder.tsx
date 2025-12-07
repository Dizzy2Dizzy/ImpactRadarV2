'use client';

import { useState } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Plus, Save, X } from 'lucide-react';

interface StrategyBuilderProps {
  strategy?: Strategy | null;
  onSaveComplete?: (strategy: Strategy) => void;
  onCancel?: () => void;
}

interface Strategy {
  id: number;
  name: string;
  description: string;
  entry_conditions: {
    event_types: string[];
    min_score: number;
    direction: 'long' | 'short' | 'both';
    tickers?: string[];
    sectors?: string[];
  };
  exit_conditions: {
    method: 'fixed_horizon' | 'trailing_stop' | 'profit_target';
    horizon_days?: number;
    take_profit_pct?: number;
    stop_loss_pct?: number;
  };
  position_sizing: {
    method: 'equal_weight' | 'score_weighted' | 'fixed_dollar';
    max_position_pct?: number;
    fixed_amount?: number;
  };
  created_at: string;
  updated_at: string;
}

const EVENT_TYPE_OPTIONS = [
  { value: 'earnings', label: 'Earnings Report' },
  { value: 'fda_approval', label: 'FDA Approval' },
  { value: 'fda_rejection', label: 'FDA Rejection' },
  { value: 'product_launch', label: 'Product Launch' },
  { value: 'merger_acquisition', label: 'M&A Announcement' },
  { value: 'guidance_raise', label: 'Guidance Raise' },
  { value: 'guidance_lower', label: 'Guidance Lower' },
  { value: 'sec_8k', label: 'SEC 8-K Filing' },
  { value: 'dividend', label: 'Dividend Announcement' },
];

const SECTOR_OPTIONS = [
  'Technology',
  'Healthcare',
  'Biotech',
  'Finance',
  'Energy',
  'Consumer',
  'Industrial',
  'Materials',
  'Utilities',
  'Real Estate',
];

export function StrategyBuilder({ strategy, onSaveComplete, onCancel }: StrategyBuilderProps) {
  const [name, setName] = useState(strategy?.name || '');
  const [description, setDescription] = useState(strategy?.description || '');
  
  const [eventTypes, setEventTypes] = useState<string[]>(strategy?.entry_conditions.event_types || []);
  const [minScore, setMinScore] = useState(strategy?.entry_conditions.min_score || 70);
  const [direction, setDirection] = useState<'long' | 'short' | 'both'>(strategy?.entry_conditions.direction || 'long');
  const [tickers, setTickers] = useState(strategy?.entry_conditions.tickers?.join(', ') || '');
  const [sectors, setSectors] = useState<string[]>(strategy?.entry_conditions.sectors || []);
  
  const [exitMethod, setExitMethod] = useState<'fixed_horizon' | 'trailing_stop' | 'profit_target'>(
    strategy?.exit_conditions.method || 'fixed_horizon'
  );
  const [horizonDays, setHorizonDays] = useState(strategy?.exit_conditions.horizon_days || 5);
  const [takeProfitPct, setTakeProfitPct] = useState(strategy?.exit_conditions.take_profit_pct || 10);
  const [stopLossPct, setStopLossPct] = useState(strategy?.exit_conditions.stop_loss_pct || 5);
  
  const [sizingMethod, setSizingMethod] = useState<'equal_weight' | 'score_weighted' | 'fixed_dollar'>(
    strategy?.position_sizing.method || 'equal_weight'
  );
  const [maxPositionPct, setMaxPositionPct] = useState(strategy?.position_sizing.max_position_pct || 10);
  const [fixedAmount, setFixedAmount] = useState(strategy?.position_sizing.fixed_amount || 10000);
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEventTypeToggle = (eventType: string) => {
    setEventTypes(prev => 
      prev.includes(eventType) 
        ? prev.filter(t => t !== eventType)
        : [...prev, eventType]
    );
  };

  const handleSectorToggle = (sector: string) => {
    setSectors(prev => 
      prev.includes(sector) 
        ? prev.filter(s => s !== sector)
        : [...prev, sector]
    );
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      if (!name.trim()) {
        throw new Error('Strategy name is required');
      }

      if (eventTypes.length === 0) {
        throw new Error('At least one event type must be selected');
      }

      const strategyData = {
        name: name.trim(),
        description: description.trim(),
        entry_conditions: {
          event_types: eventTypes,
          min_score: minScore,
          direction,
          tickers: tickers ? tickers.split(',').map(t => t.trim()).filter(Boolean) : undefined,
          sectors: sectors.length > 0 ? sectors : undefined,
        },
        exit_conditions: {
          method: exitMethod,
          horizon_days: exitMethod === 'fixed_horizon' ? horizonDays : undefined,
          take_profit_pct: exitMethod === 'profit_target' || exitMethod === 'trailing_stop' ? takeProfitPct : undefined,
          stop_loss_pct: exitMethod === 'profit_target' || exitMethod === 'trailing_stop' ? stopLossPct : undefined,
        },
        position_sizing: {
          method: sizingMethod,
          max_position_pct: sizingMethod !== 'fixed_dollar' ? maxPositionPct : undefined,
          fixed_amount: sizingMethod === 'fixed_dollar' ? fixedAmount : undefined,
        },
      };

      const url = strategy?.id 
        ? `/api/proxy/backtesting/strategies/${strategy.id}`
        : '/api/proxy/backtesting/strategies';
      
      const method = strategy?.id ? 'PUT' : 'POST';

      const savedStrategy = await apiRequest<Strategy>(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(strategyData),
      });

      if (onSaveComplete) {
        onSaveComplete(savedStrategy);
      }
    } catch (err: any) {
      console.error('Failed to save strategy:', err);
      setError(err?.message || 'Failed to save strategy');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Basic Information</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Strategy Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., FDA Approval Long Strategy"
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe your strategy..."
              rows={3}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            />
          </div>
        </div>
      </div>

      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Entry Conditions</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Event Types * (select at least one)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {EVENT_TYPE_OPTIONS.map(option => (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={eventTypes.includes(option.value)}
                    onChange={() => handleEventTypeToggle(option.value)}
                    className="rounded border-white/20 bg-white/10"
                  />
                  <span className="text-sm text-[--text]">{option.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Minimum Score (0-100)
              </label>
              <input
                type="number"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                min={0}
                max={100}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Direction
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value as any)}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
              >
                <option value="long">Long Only</option>
                <option value="short">Short Only</option>
                <option value="both">Both Long & Short</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Ticker Filters (optional, comma-separated)
            </label>
            <input
              type="text"
              value={tickers}
              onChange={(e) => setTickers(e.target.value)}
              placeholder="e.g., AAPL, MSFT, GOOGL"
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            />
            <p className="text-xs text-[--muted] mt-1">Leave empty to include all tickers</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Sector Filters (optional)
            </label>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {SECTOR_OPTIONS.map(sector => (
                <label key={sector} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={sectors.includes(sector)}
                    onChange={() => handleSectorToggle(sector)}
                    className="rounded border-white/20 bg-white/10"
                  />
                  <span className="text-sm text-[--text]">{sector}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Exit Conditions</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Exit Method
            </label>
            <select
              value={exitMethod}
              onChange={(e) => setExitMethod(e.target.value as any)}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            >
              <option value="fixed_horizon">Fixed Horizon</option>
              <option value="profit_target">Profit Target & Stop Loss</option>
              <option value="trailing_stop">Trailing Stop</option>
            </select>
          </div>

          {exitMethod === 'fixed_horizon' && (
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Hold Period (days)
              </label>
              <input
                type="number"
                value={horizonDays}
                onChange={(e) => setHorizonDays(Number(e.target.value))}
                min={1}
                max={30}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
              />
            </div>
          )}

          {(exitMethod === 'profit_target' || exitMethod === 'trailing_stop') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[--text] mb-2">
                  Take Profit (%)
                </label>
                <input
                  type="number"
                  value={takeProfitPct}
                  onChange={(e) => setTakeProfitPct(Number(e.target.value))}
                  min={1}
                  step={0.5}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[--text] mb-2">
                  Stop Loss (%)
                </label>
                <input
                  type="number"
                  value={stopLossPct}
                  onChange={(e) => setStopLossPct(Number(e.target.value))}
                  min={1}
                  step={0.5}
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Position Sizing</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Sizing Method
            </label>
            <select
              value={sizingMethod}
              onChange={(e) => setSizingMethod(e.target.value as any)}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            >
              <option value="equal_weight">Equal Weight</option>
              <option value="score_weighted">Score Weighted</option>
              <option value="fixed_dollar">Fixed Dollar Amount</option>
            </select>
          </div>

          {sizingMethod !== 'fixed_dollar' && (
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Max Position Size (% of portfolio)
              </label>
              <input
                type="number"
                value={maxPositionPct}
                onChange={(e) => setMaxPositionPct(Number(e.target.value))}
                min={1}
                max={100}
                step={1}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
              />
            </div>
          )}

          {sizingMethod === 'fixed_dollar' && (
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Fixed Dollar Amount per Trade
              </label>
              <input
                type="number"
                value={fixedAmount}
                onChange={(e) => setFixedAmount(Number(e.target.value))}
                min={100}
                step={100}
                className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
              />
            </div>
          )}
        </div>
      </div>

      <div className="flex gap-3">
        <Button
          onClick={handleSave}
          disabled={saving || !name.trim() || eventTypes.length === 0}
          className="flex-1"
        >
          {saving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              {strategy?.id ? 'Update Strategy' : 'Create Strategy'}
            </>
          )}
        </Button>

        {onCancel && (
          <Button onClick={onCancel} variant="outline">
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
        )}
      </div>
    </div>
  );
}
