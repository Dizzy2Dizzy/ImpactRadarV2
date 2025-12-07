"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, BarChart2, ArrowUpRight, ArrowDownRight, Activity, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface SectorMetrics {
  sector: string;
  win_rate: number | null;
  avg_impact: number | null;
  rotation_signal: string | null;
  momentum_score: number | null;
  total_events: number;
  snapshot_date: string | null;
}

interface PerformancePoint {
  date: string;
  win_rate: number | null;
  avg_impact: number | null;
  total_events: number;
}

interface SectorPerformance {
  sector: string;
  data: PerformancePoint[];
}

const SECTOR_COLORS = [
  "#10b981",
  "#6366f1",
  "#f59e0b",
  "#ec4899",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
  "#06b6d4",
];

export function SectorsTab() {
  const [sectors, setSectors] = useState<SectorMetrics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [performanceData, setPerformanceData] = useState<SectorPerformance[]>([]);
  const [loadingPerformance, setLoadingPerformance] = useState(false);
  const [showChart, setShowChart] = useState(false);
  
  const [sortField, setSortField] = useState<keyof SectorMetrics>("momentum_score");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    loadSectors();
  }, []);

  useEffect(() => {
    if (selectedSectors.length > 0 && showChart) {
      loadPerformanceComparison();
    }
  }, [selectedSectors, showChart]);

  const loadSectors = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/proxy/sectors");
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error("Access not available, please upgrade plan");
        }
        throw new Error("Failed to load sectors");
      }
      const data = await response.json();
      setSectors(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadSectors();
    if (selectedSectors.length > 0 && showChart) {
      await loadPerformanceComparison();
    }
    setRefreshing(false);
  };

  const loadPerformanceComparison = async () => {
    if (selectedSectors.length === 0) return;
    
    try {
      setLoadingPerformance(true);
      const params = new URLSearchParams();
      selectedSectors.forEach(s => params.append("sectors", s));
      params.append("days", "30");
      
      const response = await fetch(`/api/proxy/sectors/performance-comparison?${params.toString()}`);
      if (!response.ok) throw new Error("Failed to load performance data");
      const data = await response.json();
      setPerformanceData(data);
    } catch (err: any) {
      console.error("Failed to load performance comparison:", err);
    } finally {
      setLoadingPerformance(false);
    }
  };

  const toggleSectorSelection = (sector: string) => {
    setSelectedSectors(prev => {
      if (prev.includes(sector)) {
        return prev.filter(s => s !== sector);
      }
      if (prev.length >= 5) {
        return [...prev.slice(1), sector];
      }
      return [...prev, sector];
    });
  };

  const handleSort = (field: keyof SectorMetrics) => {
    if (sortField === field) {
      setSortDirection(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const getSortedSectors = () => {
    return [...sectors].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortDirection === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      
      const numA = Number(aVal);
      const numB = Number(bVal);
      return sortDirection === "asc" ? numA - numB : numB - numA;
    });
  };

  const inflowSectors = sectors.filter(s => s.rotation_signal === "inflow");
  const outflowSectors = sectors.filter(s => s.rotation_signal === "outflow");

  const formatWinRate = (rate: number | null) => {
    if (rate === null) return "—";
    return `${(rate * 100).toFixed(1)}%`;
  };

  const formatMomentum = (score: number | null) => {
    if (score === null) return "—";
    return score.toFixed(2);
  };

  const getSignalBadge = (signal: string | null) => {
    switch (signal) {
      case "inflow":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-[--success-soft] text-[--success] rounded text-xs font-medium">
            <ArrowUpRight className="h-3 w-3" />
            Inflow
          </span>
        );
      case "outflow":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-[--error-soft] text-[--error] rounded text-xs font-medium">
            <ArrowDownRight className="h-3 w-3" />
            Outflow
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 bg-[--muted-soft] text-[--muted] rounded text-xs font-medium">
            <Activity className="h-3 w-3" />
            Neutral
          </span>
        );
    }
  };

  const getMomentumBar = (score: number | null) => {
    if (score === null) return null;
    const percentage = Math.min(Math.max(score * 100, 0), 100);
    const color = score >= 0.6 ? "bg-[--success]" : score >= 0.4 ? "bg-[--warning]" : "bg-[--error]";
    
    return (
      <div className="flex items-center gap-2">
        <div className="w-16 h-2 bg-[--surface-glass] rounded-full overflow-hidden">
          <div 
            className={`h-full ${color} rounded-full transition-all`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-sm text-[--muted] w-10">{formatMomentum(score)}</span>
      </div>
    );
  };

  const SortHeader = ({ field, label, align = "left" }: { field: keyof SectorMetrics; label: string; align?: "left" | "right" | "center" }) => (
    <th 
      className={`p-4 text-sm font-medium text-[--muted] cursor-pointer hover:text-[--text] transition-colors text-${align}`}
      onClick={() => handleSort(field)}
    >
      <div className={`flex items-center gap-1 ${align === "right" ? "justify-end" : align === "center" ? "justify-center" : ""}`}>
        {label}
        {sortField === field && (
          sortDirection === "asc" ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
        )}
      </div>
    </th>
  );

  const formatChartDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  };

  const prepareChartData = (): Array<Record<string, string | number | null>> => {
    if (performanceData.length === 0) return [];
    
    const dateMap = new Map<string, Record<string, string | number | null>>();
    
    performanceData.forEach(sector => {
      sector.data.forEach(point => {
        if (!dateMap.has(point.date)) {
          dateMap.set(point.date, { date: point.date });
        }
        const entry = dateMap.get(point.date)!;
        entry[sector.sector] = point.win_rate ? point.win_rate * 100 : null;
      });
    });
    
    return Array.from(dateMap.values()).sort((a, b) => 
      new Date(String(a.date)).getTime() - new Date(String(b.date)).getTime()
    );
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[--card-bg] border border-[--border-strong] rounded-lg p-3 shadow-lg">
          <p className="text-sm text-[--muted] mb-2">{formatChartDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm font-semibold" style={{ color: entry.color }}>
              {entry.name}: {entry.value !== null ? `${entry.value.toFixed(1)}%` : "—"}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading sector data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[--warning-light] border border-[--border] rounded-lg p-6">
        <p className="text-[--warning]">{error}</p>
        {error.includes("upgrade") && (
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
          <h2 className="text-2xl font-bold text-[--text] mb-2">Sector Analysis</h2>
          <p className="text-sm text-[--muted]">
            Track sector rotation signals and performance metrics
          </p>
        </div>
        <Button
          onClick={handleRefresh}
          variant="outline"
          disabled={refreshing}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[--success-light] border border-[--border] rounded-lg p-4">
          <h3 className="text-sm font-semibold text-[--success] mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Sector Inflows
            <span className="ml-auto bg-[--success-soft] px-2 py-0.5 rounded-full text-xs">
              {inflowSectors.length}
            </span>
          </h3>
          {inflowSectors.length === 0 ? (
            <p className="text-sm text-[--muted]">No sectors showing strong inflows</p>
          ) : (
            <div className="space-y-2">
              {inflowSectors.map(sector => (
                <div 
                  key={sector.sector}
                  className="flex items-center justify-between p-2 bg-[--success-light] rounded hover:bg-[--surface-hover] transition-colors cursor-pointer"
                  onClick={() => toggleSectorSelection(sector.sector)}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedSectors.includes(sector.sector)}
                      onChange={() => {}}
                      className="rounded border-[--border-strong]"
                    />
                    <span className="text-sm font-medium text-[--text]">{sector.sector}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[--muted]">
                    <span>Win: {formatWinRate(sector.win_rate)}</span>
                    <span className="text-[--success] font-semibold">
                      +{formatMomentum(sector.momentum_score)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
          <h3 className="text-sm font-semibold text-[--error] mb-3 flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            Sector Outflows
            <span className="ml-auto bg-[--error-soft] px-2 py-0.5 rounded-full text-xs">
              {outflowSectors.length}
            </span>
          </h3>
          {outflowSectors.length === 0 ? (
            <p className="text-sm text-[--muted]">No sectors showing strong outflows</p>
          ) : (
            <div className="space-y-2">
              {outflowSectors.map(sector => (
                <div 
                  key={sector.sector}
                  className="flex items-center justify-between p-2 bg-[--error-light] rounded hover:bg-[--surface-hover] transition-colors cursor-pointer"
                  onClick={() => toggleSectorSelection(sector.sector)}
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedSectors.includes(sector.sector)}
                      onChange={() => {}}
                      className="rounded border-[--border-strong]"
                    />
                    <span className="text-sm font-medium text-[--text]">{sector.sector}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[--muted]">
                    <span>Win: {formatWinRate(sector.win_rate)}</span>
                    <span className="text-[--error] font-semibold">
                      {formatMomentum(sector.momentum_score)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedSectors.length > 0 && (
        <div className="bg-[--card-bg] border border-[--border] rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart2 className="h-5 w-5 text-[--muted]" />
              <h3 className="text-lg font-semibold text-[--text]">Performance Comparison</h3>
              <span className="text-xs text-[--muted]">({selectedSectors.length} selected)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex flex-wrap gap-1">
                {selectedSectors.map((sector, idx) => (
                  <span
                    key={sector}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-[--surface-glass] rounded text-xs"
                    style={{ borderLeft: `3px solid ${SECTOR_COLORS[idx % SECTOR_COLORS.length]}` }}
                  >
                    {sector}
                    <button
                      onClick={() => toggleSectorSelection(sector)}
                      className="hover:text-[--error] ml-1"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowChart(!showChart)}
              >
                {showChart ? "Hide Chart" : "Show Chart"}
              </Button>
            </div>
          </div>

          {showChart && (
            <div className="h-64 mt-4">
              {loadingPerformance ? (
                <div className="flex items-center justify-center h-full">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
                </div>
              ) : prepareChartData().length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={prepareChartData()} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                    <XAxis 
                      dataKey="date" 
                      stroke="rgba(255, 255, 255, 0.5)"
                      tick={{ fill: "rgba(255, 255, 255, 0.7)", fontSize: 12 }}
                      tickFormatter={formatChartDate}
                    />
                    <YAxis 
                      stroke="rgba(255, 255, 255, 0.5)"
                      tick={{ fill: "rgba(255, 255, 255, 0.7)", fontSize: 12 }}
                      tickFormatter={(value) => `${value}%`}
                      domain={[0, 100]}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ color: "rgba(255, 255, 255, 0.7)" }} />
                    {selectedSectors.map((sector, idx) => (
                      <Line
                        key={sector}
                        type="monotone"
                        dataKey={sector}
                        stroke={SECTOR_COLORS[idx % SECTOR_COLORS.length]}
                        strokeWidth={2}
                        name={sector}
                        dot={false}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <BarChart2 className="h-12 w-12 text-[--muted] mb-4" />
                  <p className="text-[--muted]">No historical data available</p>
                  <p className="text-sm text-[--muted] mt-1">Performance tracking requires historical snapshots</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="bg-[--card-bg] border border-[--border] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[--border] flex items-center justify-between">
          <h3 className="text-lg font-semibold text-[--text]">All Sectors</h3>
          <p className="text-sm text-[--muted]">{sectors.length} sectors tracked</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[--surface-muted]">
              <tr>
                <th className="w-8 p-4"></th>
                <SortHeader field="sector" label="Sector" />
                <SortHeader field="win_rate" label="Win Rate" align="right" />
                <SortHeader field="avg_impact" label="Avg Impact" align="right" />
                <SortHeader field="rotation_signal" label="Signal" align="center" />
                <SortHeader field="momentum_score" label="Momentum" align="right" />
                <SortHeader field="total_events" label="Events" align="right" />
              </tr>
            </thead>
            <tbody className="divide-y divide-[--border-muted]">
              {getSortedSectors().map((sector) => (
                <tr 
                  key={sector.sector} 
                  className={`hover:bg-[--surface-hover] transition-colors cursor-pointer ${
                    selectedSectors.includes(sector.sector) ? "bg-[--surface-muted]" : ""
                  }`}
                  onClick={() => toggleSectorSelection(sector.sector)}
                >
                  <td className="p-4">
                    <input
                      type="checkbox"
                      checked={selectedSectors.includes(sector.sector)}
                      onChange={() => {}}
                      className="rounded"
                    />
                  </td>
                  <td className="p-4">
                    <span className="font-medium text-[--text]">{sector.sector}</span>
                  </td>
                  <td className="p-4 text-right">
                    <span className={`font-semibold ${
                      sector.win_rate !== null 
                        ? sector.win_rate >= 0.6 
                          ? "text-[--success]" 
                          : sector.win_rate >= 0.4 
                            ? "text-[--warning]" 
                            : "text-[--error]"
                        : "text-[--muted]"
                    }`}>
                      {formatWinRate(sector.win_rate)}
                    </span>
                  </td>
                  <td className="p-4 text-right">
                    <span className="text-[--text]">
                      {sector.avg_impact !== null ? sector.avg_impact.toFixed(1) : "—"}
                    </span>
                  </td>
                  <td className="p-4 text-center">
                    {getSignalBadge(sector.rotation_signal)}
                  </td>
                  <td className="p-4">
                    <div className="flex justify-end">
                      {getMomentumBar(sector.momentum_score)}
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <span className="text-[--muted]">{sector.total_events}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sectors.length === 0 && (
          <div className="p-12 text-center">
            <Activity className="h-12 w-12 text-[--muted] mx-auto mb-4" />
            <p className="text-[--muted]">No sector data available</p>
            <p className="text-sm text-[--muted] mt-2">Sector metrics are calculated from event outcomes</p>
          </div>
        )}
      </div>
    </div>
  );
}
