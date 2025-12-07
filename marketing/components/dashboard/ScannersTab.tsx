'use client';

import { useState, useEffect } from 'react';
import { api, ScannerStatus } from '@/lib/api';
import { Activity, PlayCircle, Clock, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function ScannersTab() {
  const [scanners, setScanners] = useState<ScannerStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScanner, setSelectedScanner] = useState<string>('');
  const [scanJobs, setScanJobs] = useState<any[]>([]);
  const [isRescanning, setIsRescanning] = useState(false);

  useEffect(() => {
    loadScanners();
    // Only refresh every 30 seconds while component is mounted
    const interval = setInterval(loadScanners, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Initial load
    loadScanJobs();
    
    // Poll every 10 seconds regardless of job status (low frequency)
    // This ensures we detect new jobs even if all previous jobs finished
    const interval = setInterval(loadScanJobs, 10000);
    
    return () => clearInterval(interval);
  }, []);

  const loadScanners = async () => {
    try {
      const data = await api.scanners.getStatus();
      setScanners(data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load scanners:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load scanners');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadScanJobs = async () => {
    try {
      const response = await api.scanners.getScanJobs({ limit: 25 });
      setScanJobs(response.jobs);
    } catch (error) {
      console.error('Failed to fetch scan jobs:', error);
    }
  };

  const handleRescanScanner = async () => {
    if (!selectedScanner) {
      alert('Please select a scanner first');
      return;
    }

    // Convert display name to scanner key
    const scannerKey = getScannerKey(selectedScanner);

    setIsRescanning(true);
    try {
      const response = await api.scanners.rescanScanner(scannerKey);
      alert(`Success: ${response.message}`);
      await loadScanJobs();
    } catch (error: any) {
      const message = error?.message || 'Failed to enqueue rescan job';
      alert(`Error: ${message}`);
    } finally {
      setIsRescanning(false);
    }
  };

  const getScannerKey = (displayName: string): string => {
    // Map display names back to scanner keys for API calls
    const keyMap: { [key: string]: string } = {
      'SEC EDGAR Scanner': 'sec_edgar',
      'FDA Announcements Scanner': 'fda_announcements',
      'Company Press Releases Scanner': 'company_press',
    };
    return keyMap[displayName] || displayName.toLowerCase().replace(/ /g, '_');
  };

  const getStatusBadge = (level: string) => {
    switch (level) {
      case 'success':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--success-soft] text-[--success] rounded text-xs">
            <CheckCircle2 className="h-3 w-3" />
            Success
          </span>
        );
      case 'error':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--error-soft] text-[--error] rounded text-xs">
            <XCircle className="h-3 w-3" />
            Error
          </span>
        );
      case 'info':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--primary-soft] text-[--primary] rounded text-xs">
            <Activity className="h-3 w-3" />
            Running
          </span>
        );
      case 'pending':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--warning-soft] text-[--warning] rounded text-xs">
            <Clock className="h-3 w-3" />
            Pending
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 bg-[--surface-glass] text-[--muted] rounded text-xs">
            {level}
          </span>
        );
    }
  };

  const getJobStatusBadge = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--success-soft] text-[--success] rounded text-xs">
            <CheckCircle2 className="h-3 w-3" />
            Success
          </span>
        );
      case 'failed':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--error-soft] text-[--error] rounded text-xs">
            <XCircle className="h-3 w-3" />
            Failed
          </span>
        );
      case 'running':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--primary-soft] text-[--primary] rounded text-xs">
            <Activity className="h-3 w-3" />
            Running
          </span>
        );
      case 'pending':
        return (
          <span className="flex items-center gap-1 px-2 py-1 bg-[--warning-soft] text-[--warning] rounded text-xs">
            <Clock className="h-3 w-3" />
            Pending
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 bg-[--surface-glass] text-[--muted] rounded text-xs">
            {status}
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading scanner status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
        <p className="text-[--error]">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[--text] mb-2">Scanner Status</h2>
        <p className="text-sm text-[--muted]">
          Monitor automated scanners and trigger manual scans
        </p>
      </div>

      <div className="bg-[--surface-muted] rounded-lg p-6">
        <h3 className="font-semibold text-[--text] mb-4">Queue Manual Scan</h3>
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-[--text] mb-2">
              Select Scanner
            </label>
            <select
              value={selectedScanner}
              onChange={(e) => setSelectedScanner(e.target.value)}
              className="w-full px-3 py-2 bg-[--input-bg] border border-[--input-border] rounded-lg text-[--text]"
            >
              <option value="">Choose a scanner...</option>
              {scanners.map((scanner) => (
                <option key={scanner.scanner} value={scanner.scanner}>
                  {scanner.scanner}
                </option>
              ))}
            </select>
          </div>
          <Button
            onClick={handleRescanScanner}
            disabled={!selectedScanner || isRescanning}
            className="flex items-center gap-2"
          >
            <PlayCircle className="h-4 w-4" />
            {isRescanning ? 'Queuing...' : 'Queue Scan'}
          </Button>
        </div>
        <p className="text-xs text-[--muted] mt-2">
          Rate limit: 1 scan per 2 minutes
        </p>
      </div>

      <div>
        <h3 className="font-semibold text-[--text] mb-4">Active Scanners</h3>
        <div className="space-y-2">
          {scanners.map((scanner) => (
            <div
              key={scanner.scanner}
              className="bg-[--surface-muted] rounded-lg p-4 flex items-center justify-between"
            >
              <div className="flex items-center gap-4 flex-1">
                <Activity className="h-5 w-5 text-[--primary]" />
                <div>
                  <h4 className="font-medium text-[--text]">
                    {scanner.scanner}
                  </h4>
                  <div className="text-sm text-[--muted] space-y-1">
                    {scanner.last_run ? (
                      <p>Last run: {new Date(scanner.last_run).toLocaleString()}</p>
                    ) : (
                      <p>Never run</p>
                    )}
                    {scanner.message && <p>{scanner.message}</p>}
                    {scanner.discoveries !== undefined && scanner.discoveries > 0 && (
                      <p>{scanner.discoveries} discoveries</p>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {getStatusBadge(scanner.level)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {scanJobs.length > 0 && (
        <div>
          <h3 className="font-semibold text-[--text] mb-4">Recent Scan Jobs</h3>
          <div className="space-y-2">
            {scanJobs.map((job) => (
              <div
                key={job.id}
                className="bg-[--surface-muted] rounded-lg p-4 flex items-center justify-between"
              >
                <div className="flex-1">
                  <h4 className="font-medium text-[--text]">
                    {job.scanner_key?.replace(/_/g, ' ').toUpperCase() || 'Scanner'}
                  </h4>
                  <div className="flex items-center gap-4 text-sm text-[--muted] mt-1">
                    <span>Created: {new Date(job.created_at).toLocaleString()}</span>
                    {job.started_at && (
                      <span>Started: {new Date(job.started_at).toLocaleString()}</span>
                    )}
                    {job.finished_at && (
                      <span>Completed: {new Date(job.finished_at).toLocaleString()}</span>
                    )}
                  </div>
                  {job.items_found !== undefined && (
                    <p className="text-sm text-[--muted] mt-1">
                      Found: {job.items_found} items
                    </p>
                  )}
                </div>
                {getJobStatusBadge(job.status)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
