"use client";

import { useState, useEffect } from "react";
import { Calendar, AlertTriangle, CheckCircle, XCircle, Download, ChevronDown, ChevronUp, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { showToast } from "@/lib/toast";

interface AuditLogEntry {
  id: number;
  timestamp: string;
  entity_type: string;
  entity_id: number;
  action: string;
  performed_by: number | null;
  diff_json: Record<string, any>;
}

interface AuditLogResponse {
  total: number;
  entries: AuditLogEntry[];
  limit: number;
  offset: number;
  has_more: boolean;
}

interface ValidationFinding {
  category: string;
  check: string;
  status: "pass" | "fail" | "warning";
  message: string;
  details: Record<string, any>;
  timestamp: string;
}

interface ValidationReport {
  overall_health: "healthy" | "warning" | "critical";
  summary: {
    total_checks: number;
    passed: number;
    failed: number;
    warnings: number;
  };
  findings: ValidationFinding[];
  generated_at: string;
}

export default function AdminPage() {
  const [auditLogs, setAuditLogs] = useState<AuditLogResponse | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(0);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>("");
  const [actionFilter, setActionFilter] = useState<string>("");
  const pageSize = 50;

  useEffect(() => {
    loadData();
  }, [currentPage, entityTypeFilter, actionFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      await Promise.all([loadAuditLogs(), loadValidationReport()]);
    } catch (error: any) {
      console.error("Error loading admin data:", error);
      showToast("Failed to load admin data", "error");
    } finally {
      setLoading(false);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const offset = currentPage * pageSize;
      let url = `/api/proxy/data-quality/audit-log?limit=${pageSize}&offset=${offset}`;
      
      if (entityTypeFilter) {
        url += `&entity_type=${entityTypeFilter}`;
      }
      if (actionFilter) {
        url += `&action=${actionFilter}`;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch audit logs");
      }
      const data = await response.json();
      setAuditLogs(data);
    } catch (error: any) {
      console.error("Error loading audit logs:", error);
      throw error;
    }
  };

  const loadValidationReport = async () => {
    try {
      const response = await fetch("/api/proxy/data-quality/validation-report");
      if (!response.ok) {
        throw new Error("Failed to fetch validation report");
      }
      const data = await response.json();
      setValidationReport(data);
    } catch (error: any) {
      console.error("Error loading validation report:", error);
      throw error;
    }
  };

  const toggleRow = (id: number) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const exportToCSV = () => {
    if (!auditLogs) return;

    const headers = ["Timestamp", "Entity Type", "Entity ID", "Action", "Performed By", "Changes"];
    const rows = auditLogs.entries.map((entry) => [
      new Date(entry.timestamp).toLocaleString(),
      entry.entity_type,
      entry.entity_id,
      entry.action,
      entry.performed_by || "system",
      JSON.stringify(entry.diff_json),
    ]);

    const csv = [headers, ...rows].map((row) => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString()}.csv`;
    a.click();
    showToast("Audit log exported to CSV", "success");
  };

  const triggerValidation = async () => {
    try {
      showToast("Triggering validation...", "info");
      const response = await fetch("/api/proxy/data-quality/trigger-validation", {
        method: "POST",
      });
      
      if (!response.ok) {
        throw new Error("Failed to trigger validation");
      }
      
      showToast("Validation triggered successfully", "success");
      setTimeout(loadValidationReport, 2000);
    } catch (error: any) {
      console.error("Error triggering validation:", error);
      showToast("Failed to trigger validation", "error");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pass":
      case "healthy":
        return "text-[--success]";
      case "warning":
        return "text-[--warning]";
      case "fail":
      case "critical":
        return "text-[--error]";
      default:
        return "text-[--neutral]";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "pass":
      case "healthy":
        return <CheckCircle className="w-4 h-4" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4" />;
      case "fail":
      case "critical":
        return <XCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  if (loading && !auditLogs && !validationReport) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[--muted]">Loading admin panel...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-[--text]">Admin Panel</h2>
        <p className="text-[--muted] mt-1">
          Audit logs and data quality validation reports
        </p>
      </div>

      {/* Validation Reports Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold text-[--text]">Validation Reports</h3>
          <Button
            onClick={triggerValidation}
            className="flex items-center gap-2"
            size="sm"
          >
            <Play className="w-4 h-4" />
            Run Validation
          </Button>
        </div>

        {validationReport ? (
          <div className="space-y-4">
            {/* Overall Health */}
            <div className="border border-white/10 rounded-lg p-6 bg-[--card]">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-semibold text-[--text]">Overall Health</h4>
                <div className={`flex items-center gap-2 ${getStatusColor(validationReport.overall_health)}`}>
                  {getStatusIcon(validationReport.overall_health)}
                  <span className="font-medium capitalize">{validationReport.overall_health}</span>
                </div>
              </div>

              <div className="grid grid-cols-4 gap-4">
                <div>
                  <div className="text-[--muted] text-sm">Total Checks</div>
                  <div className="text-2xl font-bold text-[--text]">
                    {validationReport.summary.total_checks}
                  </div>
                </div>
                <div>
                  <div className="text-[--muted] text-sm">Passed</div>
                  <div className="text-2xl font-bold text-[--success]">
                    {validationReport.summary.passed}
                  </div>
                </div>
                <div>
                  <div className="text-[--muted] text-sm">Warnings</div>
                  <div className="text-2xl font-bold text-[--warning]">
                    {validationReport.summary.warnings}
                  </div>
                </div>
                <div>
                  <div className="text-[--muted] text-sm">Failed</div>
                  <div className="text-2xl font-bold text-[--error]">
                    {validationReport.summary.failed}
                  </div>
                </div>
              </div>

              <div className="mt-4 text-xs text-[--muted]">
                Last updated: {new Date(validationReport.generated_at).toLocaleString()}
              </div>
            </div>

            {/* Findings by Category */}
            <div className="border border-white/10 rounded-lg overflow-hidden bg-[--card]">
              <div className="p-4 border-b border-white/10">
                <h4 className="font-semibold text-[--text]">Validation Findings</h4>
              </div>
              <div className="divide-y divide-white/10">
                {validationReport.findings.map((finding, index) => (
                  <div key={index} className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <div className={getStatusColor(finding.status)}>
                            {getStatusIcon(finding.status)}
                          </div>
                          <div>
                            <div className="font-medium text-[--text]">
                              {finding.category} - {finding.check}
                            </div>
                            <div className="text-sm text-[--muted] mt-1">
                              {finding.message}
                            </div>
                            {Object.keys(finding.details).length > 0 && (
                              <div className="mt-2 text-xs text-[--muted] font-mono bg-black/20 rounded p-2">
                                {JSON.stringify(finding.details, null, 2)}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(finding.status)}`}>
                        {finding.status.toUpperCase()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="border border-white/10 rounded-lg p-8 text-center text-[--muted] bg-[--card]">
            No validation report available
          </div>
        )}
      </div>

      {/* Audit Log Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold text-[--text]">Audit Log</h3>
          <Button
            onClick={exportToCSV}
            className="flex items-center gap-2"
            size="sm"
            disabled={!auditLogs || auditLogs.entries.length === 0}
          >
            <Download className="w-4 h-4" />
            Export CSV
          </Button>
        </div>

        {/* Filters */}
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="text-sm text-[--muted] block mb-1">Entity Type</label>
            <select
              value={entityTypeFilter}
              onChange={(e) => {
                setEntityTypeFilter(e.target.value);
                setCurrentPage(0);
              }}
              className="w-full px-3 py-2 bg-[--card] border border-white/10 rounded-lg text-[--text] focus:outline-none focus:ring-2 focus:ring-[--primary]"
            >
              <option value="">All Types</option>
              <option value="event">Event</option>
              <option value="outcome_labeling">Outcome Labeling</option>
              <option value="user">User</option>
              <option value="pipeline">Pipeline</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="text-sm text-[--muted] block mb-1">Action</label>
            <select
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setCurrentPage(0);
              }}
              className="w-full px-3 py-2 bg-[--card] border border-white/10 rounded-lg text-[--text] focus:outline-none focus:ring-2 focus:ring-[--primary]"
            >
              <option value="">All Actions</option>
              <option value="create">Create</option>
              <option value="update">Update</option>
              <option value="delete">Delete</option>
            </select>
          </div>
        </div>

        {/* Audit Log Table */}
        {auditLogs && auditLogs.entries.length > 0 ? (
          <div className="border border-white/10 rounded-lg overflow-hidden bg-[--card]">
            <table className="w-full">
              <thead className="bg-black/20">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Timestamp
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Entity Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Entity ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Action
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Performed By
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {auditLogs.entries.map((entry) => (
                  <>
                    <tr
                      key={entry.id}
                      className="hover:bg-white/5 cursor-pointer"
                      onClick={() => toggleRow(entry.id)}
                    >
                      <td className="px-4 py-3 text-sm text-[--text]">
                        {new Date(entry.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-sm text-[--text]">
                        {entry.entity_type}
                      </td>
                      <td className="px-4 py-3 text-sm text-[--text]">
                        {entry.entity_id}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            entry.action === "create"
                              ? "bg-green-500/10 text-green-400"
                              : entry.action === "update"
                              ? "bg-blue-500/10 text-blue-400"
                              : "bg-red-500/10 text-red-400"
                          }`}
                        >
                          {entry.action.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[--muted]">
                        {entry.performed_by || "system"}
                      </td>
                      <td className="px-4 py-3 text-sm text-[--text]">
                        {expandedRows.has(entry.id) ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </td>
                    </tr>
                    {expandedRows.has(entry.id) && (
                      <tr>
                        <td colSpan={6} className="px-4 py-3 bg-black/20">
                          <div className="text-xs text-[--muted] font-mono">
                            <pre className="whitespace-pre-wrap overflow-x-auto">
                              {JSON.stringify(entry.diff_json, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between">
              <div className="text-sm text-[--muted]">
                Showing {auditLogs.offset + 1} to {Math.min(auditLogs.offset + auditLogs.limit, auditLogs.total)} of{" "}
                {auditLogs.total} entries
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 0}
                  size="sm"
                  variant="outline"
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={!auditLogs.has_more}
                  size="sm"
                  variant="outline"
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <div className="border border-white/10 rounded-lg p-8 text-center text-[--muted] bg-[--card]">
            No audit log entries found
          </div>
        )}
      </div>
    </div>
  );
}
