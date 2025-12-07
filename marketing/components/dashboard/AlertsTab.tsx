'use client';

import { useState, useEffect } from 'react';
import { api, Alert, AlertCreate, PatternAlert } from '@/lib/api';
import { Plus, Edit2, Trash2, Bell, BellOff, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { PatternAlertCard } from './PatternAlertCard';

export function AlertsTab() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [patternAlerts, setPatternAlerts] = useState<PatternAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingAlert, setEditingAlert] = useState<Alert | null>(null);
  
  const [formData, setFormData] = useState<AlertCreate>({
    name: '',
    min_score: 70,
    tickers: [],
    sectors: [],
    event_types: [],
    keywords: [],
    channels: ['in_app'],
    active: true,
  });
  const [tickerInput, setTickerInput] = useState('');
  const [keywordInput, setKeywordInput] = useState('');

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch both regular alerts and pattern alerts
      const [regularAlerts, patterns] = await Promise.all([
        api.alerts.getAll(),
        api.patterns.getPatternAlerts({ limit: 50 }).catch(() => []), // Don't fail if pattern alerts fail
      ]);
      
      setAlerts(regularAlerts);
      setPatternAlerts(patterns);
    } catch (err: any) {
      console.error('Failed to load alerts:', err);
      if (err.status === 403 || err.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else if (err.status === 402 || err.message?.includes('402')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load alerts');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.alerts.create(formData);
      await loadAlerts();
      setShowCreateDialog(false);
      resetForm();
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to create alert';
      
      // Show user-friendly error for phone number issues
      if (errorMessage.includes('Phone number required') || errorMessage.includes('phone')) {
        alert(
          'SMS notifications require a verified phone number.\n\n' +
          'Please add a phone number to your profile in Account Settings, ' +
          'or remove SMS from the notification channels.'
        );
      } else {
        alert(errorMessage);
      }
    }
  };

  const handleUpdate = async () => {
    if (!editingAlert) return;
    
    try {
      await api.alerts.update(editingAlert.id, formData);
      await loadAlerts();
      setEditingAlert(null);
      resetForm();
    } catch (err: any) {
      const errorMessage = err?.message || 'Failed to update alert';
      
      // Show user-friendly error for phone number issues
      if (errorMessage.includes('Phone number required') || errorMessage.includes('phone')) {
        alert(
          'SMS notifications require a verified phone number.\n\n' +
          'Please add a phone number to your profile in Account Settings, ' +
          'or remove SMS from the notification channels.'
        );
      } else {
        alert(errorMessage);
      }
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this alert?')) return;
    
    try {
      await api.alerts.delete(id);
      await loadAlerts();
    } catch (err: any) {
      alert(err?.message || 'Failed to delete alert');
    }
  };

  const handleToggleActive = async (alertItem: Alert) => {
    try {
      await api.alerts.update(alertItem.id, { active: !alertItem.active });
      await loadAlerts();
    } catch (err: any) {
      window.alert(err?.message || 'Failed to update alert');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      min_score: 70,
      tickers: [],
      sectors: [],
      event_types: [],
      keywords: [],
      channels: ['in_app'],
      active: true,
    });
    setTickerInput('');
    setKeywordInput('');
  };

  const handleEdit = (alert: Alert) => {
    setEditingAlert(alert);
    setFormData({
      name: alert.name,
      min_score: alert.min_score,
      tickers: alert.tickers || [],
      sectors: alert.sectors || [],
      event_types: alert.event_types || [],
      keywords: alert.keywords || [],
      channels: alert.channels,
      active: alert.active,
    });
  };

  const addTicker = () => {
    if (tickerInput && !formData.tickers?.includes(tickerInput.toUpperCase())) {
      setFormData(prev => ({
        ...prev,
        tickers: [...(prev.tickers || []), tickerInput.toUpperCase()],
      }));
      setTickerInput('');
    }
  };

  const removeTicker = (ticker: string) => {
    setFormData(prev => ({
      ...prev,
      tickers: (prev.tickers || []).filter(t => t !== ticker),
    }));
  };

  const addKeyword = () => {
    if (keywordInput && !formData.keywords?.includes(keywordInput)) {
      setFormData(prev => ({
        ...prev,
        keywords: [...(prev.keywords || []), keywordInput],
      }));
      setKeywordInput('');
    }
  };

  const removeKeyword = (keyword: string) => {
    setFormData(prev => ({
      ...prev,
      keywords: (prev.keywords || []).filter(k => k !== keyword),
    }));
  };

  const handleAcknowledgePatternAlert = async (alertId: number) => {
    try {
      await api.patterns.acknowledgePatternAlert(alertId);
      await loadAlerts(); // Reload to update the status
    } catch (err: any) {
      alert(err?.message || 'Failed to acknowledge pattern alert');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-[--muted]">Loading alerts...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-6">
        <p className="text-yellow-400">{error}</p>
        {error.includes('Pro and Team') && (
          <Button className="mt-4" asChild>
            <a href="/pricing">Upgrade Plan</a>
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[--text] mb-2">Alerts</h2>
          <p className="text-sm text-[--muted]">
            Get notified when important events match your criteria
          </p>
        </div>
        <Button
          onClick={() => setShowCreateDialog(true)}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Create Alert
        </Button>
      </div>

      {/* Pattern Alerts Section */}
      {patternAlerts.length > 0 && (
        <div className="space-y-4">
          <div className="border-b border-[--border] pb-2">
            <h3 className="text-xl font-semibold text-[--text] flex items-center gap-2">
              <span className="px-2 py-1 bg-[--primary-soft] text-[--primary] rounded text-sm">
                Pattern Alerts
              </span>
              <span className="text-sm text-[--muted] font-normal">
                ({patternAlerts.filter(a => a.status !== 'acknowledged').length} active)
              </span>
            </h3>
            <p className="text-xs text-[--muted] mt-1">
              Multi-event correlations detected across your watchlist
            </p>
          </div>
          
          <div className="space-y-3">
            {patternAlerts.map((alert) => (
              <PatternAlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledgePatternAlert}
              />
            ))}
          </div>
        </div>
      )}

      {/* Divider between pattern alerts and regular alerts */}
      {patternAlerts.length > 0 && (
        <div className="border-t border-[--border] pt-2">
          <h3 className="text-xl font-semibold text-[--text] mb-1">Event Alerts</h3>
          <p className="text-xs text-[--muted]">
            Individual event notifications based on your criteria
          </p>
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="text-center py-12 bg-[--surface-muted] rounded-lg">
          <Bell className="h-12 w-12 text-[--muted] mx-auto mb-4" />
          <p className="text-[--muted] mb-4">No alerts configured yet</p>
          <Button onClick={() => setShowCreateDialog(true)}>Create Your First Alert</Button>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-[--surface-muted] rounded-lg p-6 hover:bg-[--surface-hover] transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-[--text]">{alert.name}</h3>
                    {alert.active ? (
                      <span className="px-2 py-1 bg-[--badge-positive-bg] text-[--badge-positive-text] rounded text-xs">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-[--badge-neutral-bg] text-[--badge-neutral-text] rounded text-xs">
                        Inactive
                      </span>
                    )}
                  </div>

                  <div className="space-y-2 text-sm text-[--muted]">
                    <p>Minimum Score: {alert.min_score}</p>
                    
                    {alert.tickers && alert.tickers.length > 0 && (
                      <p>Tickers: {alert.tickers.join(', ')}</p>
                    )}
                    
                    {alert.sectors && alert.sectors.length > 0 && (
                      <p>Sectors: {alert.sectors.join(', ')}</p>
                    )}
                    
                    {alert.event_types && alert.event_types.length > 0 && (
                      <p>Event Types: {alert.event_types.map(t => t.replace(/_/g, ' ')).join(', ')}</p>
                    )}
                    
                    {alert.keywords && alert.keywords.length > 0 && (
                      <p>Keywords: {alert.keywords.join(', ')}</p>
                    )}
                    
                    <p>Channels: {alert.channels.join(', ')}</p>
                    <p className="text-xs">Created: {new Date(alert.created_at).toLocaleString()}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleActive(alert)}
                    className="p-2 hover:bg-[--surface-hover] rounded transition-colors"
                    title={alert.active ? 'Disable alert' : 'Enable alert'}
                  >
                    {alert.active ? (
                      <Bell className="h-5 w-5 text-[--success]" />
                    ) : (
                      <BellOff className="h-5 w-5 text-[--muted]" />
                    )}
                  </button>
                  <button
                    onClick={() => handleEdit(alert)}
                    className="p-2 hover:bg-[--surface-hover] rounded transition-colors"
                  >
                    <Edit2 className="h-5 w-5 text-[--primary]" />
                  </button>
                  <button
                    onClick={() => handleDelete(alert.id)}
                    className="p-2 hover:bg-[--surface-hover] rounded transition-colors"
                  >
                    <Trash2 className="h-5 w-5 text-[--error]" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={showCreateDialog || editingAlert !== null} onOpenChange={(open) => {
        if (!open) {
          setShowCreateDialog(false);
          setEditingAlert(null);
          resetForm();
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingAlert ? 'Edit Alert' : 'Create Alert'}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Alert Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., High Impact Biotech Events"
                className="w-full px-3 py-2 bg-[--input-bg] border border-[--input-border] rounded-lg text-[--text]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Minimum Score: {formData.min_score}
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={formData.min_score}
                onChange={(e) => setFormData(prev => ({ ...prev, min_score: parseInt(e.target.value) }))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Tickers (optional)
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTicker())}
                  placeholder="e.g., AAPL"
                  className="flex-1 px-3 py-2 bg-[--input-bg] border border-[--input-border] rounded-lg text-[--text]"
                />
                <Button onClick={addTicker} type="button">Add</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.tickers?.map(ticker => (
                  <span
                    key={ticker}
                    className="px-3 py-1 bg-[--surface-muted] rounded-full text-sm flex items-center gap-2"
                  >
                    {ticker}
                    <button onClick={() => removeTicker(ticker)} className="text-[--error] hover:opacity-80">
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Keywords (optional)
              </label>
              <div className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addKeyword())}
                  placeholder="e.g., FDA approval"
                  className="flex-1 px-3 py-2 bg-[--input-bg] border border-[--input-border] rounded-lg text-[--text]"
                />
                <Button onClick={addKeyword} type="button">Add</Button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.keywords?.map(keyword => (
                  <span
                    key={keyword}
                    className="px-3 py-1 bg-[--surface-muted] rounded-full text-sm flex items-center gap-2"
                  >
                    {keyword}
                    <button onClick={() => removeKeyword(keyword)} className="text-[--error] hover:opacity-80">
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Notification Channels
              </label>
              <div className="space-y-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.channels?.includes('in_app')}
                    onChange={(e) => {
                      const channels = e.target.checked
                        ? [...(formData.channels || []), 'in_app']
                        : (formData.channels || []).filter(c => c !== 'in_app');
                      setFormData(prev => ({ ...prev, channels }));
                    }}
                  />
                  <span className="text-[--text]">In-App Notifications</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.channels?.includes('email')}
                    onChange={(e) => {
                      const channels = e.target.checked
                        ? [...(formData.channels || []), 'email']
                        : (formData.channels || []).filter(c => c !== 'email');
                      setFormData(prev => ({ ...prev, channels }));
                    }}
                  />
                  <span className="text-[--text]">Email</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.channels?.includes('sms')}
                    onChange={(e) => {
                      const channels = e.target.checked
                        ? [...(formData.channels || []), 'sms']
                        : (formData.channels || []).filter(c => c !== 'sms');
                      setFormData(prev => ({ ...prev, channels }));
                    }}
                  />
                  <span className="text-[--text]">SMS (Text Message)</span>
                </label>
              </div>
              
              {formData.channels?.includes('sms') && (
                <div className="mt-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-start gap-2">
                  <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-300">
                    <p className="font-medium mb-1">Phone Number Required</p>
                    <p className="text-blue-200/80">
                      SMS notifications require a verified phone number in E.164 format (e.g., +14155551234). 
                      Rate limit: 10 SMS per day.
                    </p>
                    <p className="text-blue-200/80 mt-1">
                      Don't have a phone number on your account? Add one in the{' '}
                      <strong className="text-blue-100">Account tab</strong> above (Account Management section).
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-3 pt-4">
              <Button onClick={editingAlert ? handleUpdate : handleCreate} className="flex-1">
                {editingAlert ? 'Update Alert' : 'Create Alert'}
              </Button>
              <Button
                onClick={() => {
                  setShowCreateDialog(false);
                  setEditingAlert(null);
                  resetForm();
                }}
                variant="outline"
              >
                Cancel
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
