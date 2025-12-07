"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Upload, FileDown, Trash2, TrendingUp, TrendingDown, Calculator, Loader2 } from "lucide-react";
import { 
  portfolioAPI, 
  type PortfolioInsightsEvent,
  type RiskSnapshotResponse,
  type EventExposure,
  type PortfolioInsight
} from "@/lib/api";
import { RiskMetricsCards } from "./RiskMetricsCards";
import { EventExposureTable } from "./EventExposureTable";
import { SectorCorrelationMatrix } from "./SectorCorrelationMatrix";

export function PortfolioTab() {
  const [positions, setPositions] = useState<any[]>([]);
  const [insights, setInsights] = useState<PortfolioInsightsEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<Array<{ row: number; field: string; message: string }>>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [portfolioId, setPortfolioId] = useState<number | null>(null);
  const [riskSnapshot, setRiskSnapshot] = useState<RiskSnapshotResponse | null>(null);
  const [eventExposures, setEventExposures] = useState<EventExposure[]>([]);
  const [calculatingRisk, setCalculatingRisk] = useState(false);
  const [loadingRisk, setLoadingRisk] = useState(false);

  useEffect(() => {
    loadPortfolio();
  }, []);

  const loadPortfolio = async () => {
    setLoading(true);
    try {
      const portfolioData = await portfolioAPI.get().catch(() => null);
      
      if (!portfolioData?.id) {
        setPositions([]);
        setInsights([]);
        setPortfolioId(null);
        setRiskSnapshot(null);
        setEventExposures([]);
        return;
      }
      
      setPortfolioId(portfolioData.id);
      
      const holdings = await portfolioAPI.getHoldings().catch(() => []);
      setPositions(holdings || []);
      
      if (holdings && holdings.length > 0) {
        try {
          const rawInsights: PortfolioInsight[] = await portfolioAPI.insights({ days_ahead: 30 });
          
          const flatEvents: PortfolioInsightsEvent[] = [];
          const now = new Date();
          
          for (const position of rawInsights || []) {
            const holdingData = holdings.find((h) => h.ticker === position.ticker);
            const lastPrice = holdingData?.current_price || holdingData?.cost_basis || 0;
            const qty = position.shares || 0;
            
            for (const event of position.events || []) {
              const eventDate = new Date(event.date);
              const daysUntil = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
              const expectedMove = event.score ? event.score / 20 / 100 : 0.02;
              
              flatEvents.push({
                event_id: flatEvents.length,
                ticker: position.ticker,
                event_type: 'catalyst',
                headline: event.title,
                date: event.date,
                days_until: daysUntil,
                final_score: event.score || 50,
                direction: event.direction || 'neutral',
                confidence: 0.75,
                expected_move_1d: expectedMove,
                expected_move_5d: expectedMove * 1.5,
                expected_move_20d: null,
                sample_size_1d: 10,
                qty: qty,
                last_price: lastPrice,
                exposure_1d: position.exposure_1d / (position.events?.length || 1),
              });
            }
          }
          
          flatEvents.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
          setInsights(flatEvents);
        } catch (err) {
          console.error("Failed to load insights:", err);
          setInsights([]);
        }
        
        setLoadingRisk(true);
        try {
          const [snapshot, exposures] = await Promise.all([
            portfolioAPI.getLatestRiskSnapshot(portfolioData.id).catch(() => null),
            portfolioAPI.getEventExposures(portfolioData.id, 30).catch(() => [])
          ]);
          setRiskSnapshot(snapshot);
          setEventExposures(exposures || []);
        } catch (err) {
          console.error("Failed to load risk data:", err);
          setRiskSnapshot(null);
          setEventExposures([]);
        } finally {
          setLoadingRisk(false);
        }
      } else {
        setInsights([]);
        setRiskSnapshot(null);
        setEventExposures([]);
      }
    } catch (error: any) {
      console.error("Failed to load portfolio:", error);
      setPositions([]);
      setInsights([]);
      setRiskSnapshot(null);
      setEventExposures([]);
    } finally {
      setLoading(false);
    }
  };

  const loadRiskData = async () => {
    if (!portfolioId) return;
    
    setLoadingRisk(true);
    try {
      const [snapshot, exposures] = await Promise.all([
        portfolioAPI.getLatestRiskSnapshot(portfolioId).catch(() => null),
        portfolioAPI.getEventExposures(portfolioId, 30).catch(() => [])
      ]);
      
      setRiskSnapshot(snapshot);
      setEventExposures(exposures);
    } catch (error: any) {
      console.error("Failed to load risk data:", error);
    } finally {
      setLoadingRisk(false);
    }
  };

  const handleCalculateRisk = async () => {
    if (!portfolioId) {
      setActionError("Portfolio ID not found. Please re-upload your portfolio.");
      return;
    }

    setCalculatingRisk(true);
    setActionError(null);
    try {
      await portfolioAPI.calculateRisk(portfolioId, 30);
      await loadRiskData();
    } catch (error: any) {
      setActionError(error.message || "Failed to calculate risk. Please try again.");
    } finally {
      setCalculatingRisk(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadErrors([]);
    setActionError(null);

    try {
      const response = await portfolioAPI.upload(file);
      if (response.success) {
        setPortfolioId(response.portfolio_id);
        await loadPortfolio();
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
      if (response.errors && response.errors.length > 0) {
        setUploadErrors(response.errors);
      }
    } catch (error: any) {
      setActionError(error.message || "Failed to upload portfolio");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete your portfolio? This action cannot be undone.")) {
      return;
    }

    setActionError(null);
    try {
      await portfolioAPI.delete();
      setPortfolioId(null);
      setRiskSnapshot(null);
      setEventExposures([]);
      await loadPortfolio();
    } catch (error: any) {
      setActionError(error.message || "Failed to delete portfolio");
    }
  };

  const handleExport = async () => {
    setActionError(null);
    try {
      setExporting(true);
      
      const url = '/api/proxy/portfolio/export?window_days=30';
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      const today = new Date().toISOString().split('T')[0];
      link.download = `impactradar_portfolio_${today}.csv`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (err: any) {
      console.error('Failed to export portfolio:', err);
      setActionError('Failed to export portfolio analysis. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const downloadTemplate = () => {
    const csvContent = "ticker,qty,avg_price,as_of\nAAPL,100,150.00,2024-01-15\nMRNA,50,200.00,2024-01-20\n";
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'portfolio_template.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getScoreColor = (score: number) => {
    if (score >= 76) return 'text-[--success]';
    if (score >= 51) return 'text-[--primary]';
    if (score >= 26) return 'text-[--warning]';
    return 'text-[--error]';
  };

  const getDirectionColor = (direction: string) => {
    if (direction === 'positive') return 'text-[--success]';
    if (direction === 'negative') return 'text-[--error]';
    if (direction === 'neutral') return 'text-[--muted]';
    return 'text-[--warning]';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-[--muted]">Loading portfolio...</p>
      </div>
    );
  }

  if (positions.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-semibold text-[--text]">Portfolio Risk</h2>
            <p className="text-sm text-[--muted]">Upload your holdings to see upcoming catalysts and typical moves</p>
          </div>
        </div>

        <div className="rounded-lg border border-[--border] bg-[--panel] p-12 text-center">
          <div className="max-w-md mx-auto space-y-4">
            <Upload className="h-12 w-12 text-[--muted] mx-auto" />
            <h3 className="text-lg font-semibold text-[--text]">No Portfolio Uploaded</h3>
            <p className="text-sm text-[--muted]">
              Upload a CSV file with your positions to see upcoming events and exposure calculations
            </p>
            
            <div className="space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleUpload}
                className="hidden"
              />
              <Button 
                onClick={() => fileInputRef.current?.click()} 
                disabled={uploading}
                className="w-full"
              >
                {uploading ? "Uploading..." : "Upload Portfolio CSV"}
              </Button>
              
              <button
                onClick={downloadTemplate}
                className="text-sm text-[--primary] hover:text-[--primary] flex items-center gap-2 mx-auto"
              >
                <FileDown className="h-4 w-4" />
                Download CSV Template
              </button>
            </div>

            <div className="text-xs text-[--muted] text-left bg-[--surface-strong] p-4 rounded-lg border border-[--border-muted]">
              <p className="font-medium mb-2">CSV Format:</p>
              <code className="block whitespace-pre font-mono">
                ticker,qty,avg_price,as_of{'\n'}
                AAPL,100,150.00,2024-01-15{'\n'}
                MRNA,50,200.00,2024-01-20
              </code>
            </div>
          </div>
        </div>

        {uploadErrors.length > 0 && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
            <h4 className="text-sm font-medium text-[--error] mb-2">Upload Errors:</h4>
            <ul className="text-xs text-[--error] space-y-1">
              {uploadErrors.map((error, idx) => (
                <li key={idx}>
                  Row {error.row}, {error.field}: {error.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {actionError && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
            <p className="text-sm text-[--error]">{actionError}</p>
            <button
              onClick={() => setActionError(null)}
              className="text-xs text-[--error] hover:text-[--error] mt-2 underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-[--text]">Portfolio Risk</h2>
          <p className="text-sm text-[--muted]">{positions.length} positions, {insights.length} upcoming events</p>
        </div>
        <div className="flex gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleUpload}
            className="hidden"
          />
          <Button 
            onClick={handleExport}
            disabled={exporting}
            variant="outline"
          >
            <FileDown className="h-4 w-4 mr-2" />
            {exporting ? "Exporting..." : "Export Analysis"}
          </Button>
          <Button 
            onClick={() => fileInputRef.current?.click()} 
            disabled={uploading}
            variant="outline"
          >
            {uploading ? "Uploading..." : "Re-upload"}
          </Button>
          <Button 
            onClick={handleDelete}
            variant="outline"
            className="text-[--error] hover:text-[--error]"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {uploadErrors.length > 0 && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <h4 className="text-sm font-medium text-[--error] mb-2">Upload Errors:</h4>
          <ul className="text-xs text-[--error] space-y-1">
            {uploadErrors.map((error, idx) => (
              <li key={idx}>
                Row {error.row}, {error.field}: {error.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {actionError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <p className="text-sm text-[--error]">{actionError}</p>
          <button
            onClick={() => setActionError(null)}
            className="text-xs text-[--error] hover:text-[--error] mt-2 underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-[--text]">Upcoming Events</h3>
        {insights.length === 0 ? (
          <div className="rounded-lg border border-[--border] bg-[--panel] p-8 text-center">
            <p className="text-[--muted]">No upcoming events found for your positions in the next 30 days</p>
          </div>
        ) : (
          <div className="rounded-lg border border-[--border] bg-[--panel] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[--border] bg-[--surface-strong]">
                    <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Ticker</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Event</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Date</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Score</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Direction</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Typical 1D Move</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Exposure</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[--border-muted]">
                  {insights.map((event, idx) => (
                    <tr key={idx} className="hover:bg-[--surface-hover] transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-mono font-semibold text-[--text]">{event.ticker}</div>
                        <div className="text-xs text-[--muted]">{event.qty > 0 ? 'Long' : 'Short'} {Math.abs(event.qty)} @ ${event.last_price.toFixed(2)}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-[--text] max-w-xs truncate">{event.headline}</div>
                        <div className="text-xs text-[--muted]">{event.event_type}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="text-sm text-[--text]">{formatDate(event.date)}</div>
                        <div className="text-xs text-[--muted]">{event.days_until} days</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-semibold ${getScoreColor(event.final_score)}`}>
                          {event.final_score}
                        </span>
                        <div className="text-xs text-[--muted]">{Math.round(event.confidence * 100)}% conf</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className={`text-sm font-medium ${getDirectionColor(event.direction)}`}>
                          {event.direction}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {event.expected_move_1d !== null && event.sample_size_1d !== null && event.sample_size_1d > 0 ? (
                          <>
                            <div className={`text-sm font-medium ${event.expected_move_1d >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                              {event.expected_move_1d >= 0 ? <TrendingUp className="inline h-3 w-3" /> : <TrendingDown className="inline h-3 w-3" />}
                              {' '}{(event.expected_move_1d * 100).toFixed(1)}%
                            </div>
                            <div className="text-xs text-[--muted]">n={event.sample_size_1d}</div>
                          </>
                        ) : (
                          <span className="text-xs text-[--muted]">No data</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className={`text-sm font-semibold ${event.exposure_1d >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                          ${Math.abs(event.exposure_1d).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {portfolioId && (
        <div className="space-y-6 mt-8 pt-8 border-t border-[--border]">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-xl font-semibold text-[--text]">Risk Analysis</h3>
              <p className="text-sm text-[--muted]">Comprehensive portfolio risk metrics and exposure analysis</p>
            </div>
            <Button 
              onClick={handleCalculateRisk}
              disabled={calculatingRisk || loadingRisk}
              className="flex items-center gap-2"
            >
              {calculatingRisk ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Calculating...
                </>
              ) : (
                <>
                  <Calculator className="h-4 w-4" />
                  Calculate Risk
                </>
              )}
            </Button>
          </div>

          {loadingRisk ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-[--muted]" />
            </div>
          ) : riskSnapshot ? (
            <div className="space-y-6">
              <RiskMetricsCards metrics={riskSnapshot.metrics} />
              
              <div className="space-y-4">
                <h4 className="text-lg font-semibold text-[--text]">Event-Level Exposure</h4>
                <EventExposureTable exposures={eventExposures} />
              </div>

              <div className="space-y-4">
                <h4 className="text-lg font-semibold text-[--text]">Sector Correlation</h4>
                <SectorCorrelationMatrix correlationData={{}} />
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-[--border] bg-[--panel] p-8 text-center">
              <Calculator className="h-12 w-12 text-[--muted] mx-auto mb-4" />
              <p className="text-[--muted] mb-4">No risk analysis available yet</p>
              <p className="text-sm text-[--muted]">
                Click "Calculate Risk" above to generate comprehensive risk metrics for your portfolio
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
