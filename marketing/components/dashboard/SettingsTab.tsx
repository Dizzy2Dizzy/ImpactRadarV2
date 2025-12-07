"use client";

import { useState, useEffect } from "react";
import { Sun, Moon, Monitor, Save, Mail, Download, Filter, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { showToast } from "@/lib/toast";

interface UserPreferences {
  theme: string;
  default_horizon: string;
  saved_filters: SavedFilters;
  notification_settings: Record<string, any>;
  timezone: string;
}

interface SavedFilters {
  event_types: string[];
  sectors: string[];
  min_score: number;
  horizons: string[];
}

interface DigestSubscription {
  id: number;
  frequency: string;
  delivery_time: string;
  delivery_day: number | null;
  active: boolean;
  next_send_at: string | null;
}

const EVENT_TYPES = [
  "earnings",
  "fda_approval",
  "merger_acquisition",
  "product_launch",
  "regulatory",
  "guidance",
  "clinical_trial",
  "insider_trade",
];

const SECTORS = [
  "Technology",
  "Healthcare",
  "Financials",
  "Consumer",
  "Energy",
  "Industrials",
  "Materials",
  "Utilities",
];

const HORIZONS = ["1d", "7d", "30d", "90d"];

export function SettingsTab() {
  const [theme, setTheme] = useState<string>("system");
  const [savedFilters, setSavedFilters] = useState<SavedFilters>({
    event_types: [],
    sectors: [],
    min_score: 0,
    horizons: ["1d", "7d"],
  });
  const [digest, setDigest] = useState<DigestSubscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingTheme, setSavingTheme] = useState(false);
  const [savingFilters, setSavingFilters] = useState(false);
  const [savingDigest, setSavingDigest] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const [themeRes, filtersRes, digestRes] = await Promise.all([
        fetch("/api/proxy/preferences/theme").catch(() => null),
        fetch("/api/proxy/preferences/filters").catch(() => null),
        fetch("/api/proxy/digests").catch(() => null),
      ]);

      if (themeRes?.ok) {
        const data = await themeRes.json();
        setTheme(data.theme || "system");
        applyTheme(data.theme);
      }
      if (filtersRes?.ok) {
        const data = await filtersRes.json();
        setSavedFilters({
          event_types: data.event_types || [],
          sectors: data.sectors || [],
          min_score: data.min_score || 0,
          horizons: data.horizons || ["1d", "7d"],
        });
      }
      if (digestRes?.ok) {
        const data = await digestRes.json();
        setDigest(data);
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  const applyTheme = (newTheme: string) => {
    if (newTheme === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.setAttribute("data-theme", "dark");
    } else if (newTheme === "light") {
      document.documentElement.classList.remove("dark");
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      document.documentElement.classList.toggle("dark", prefersDark);
      document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
    }
    localStorage.setItem("theme", newTheme);
  };

  const handleThemeChange = async (newTheme: string) => {
    try {
      setSavingTheme(true);
      setTheme(newTheme);
      applyTheme(newTheme);

      await fetch("/api/proxy/preferences/theme", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ theme: newTheme }),
      });

      showToast("Theme updated", "success");
    } catch (err) {
      showToast("Failed to save theme", "error");
    } finally {
      setSavingTheme(false);
    }
  };

  const toggleEventType = (eventType: string) => {
    setSavedFilters((prev) => ({
      ...prev,
      event_types: prev.event_types.includes(eventType)
        ? prev.event_types.filter((t) => t !== eventType)
        : [...prev.event_types, eventType],
    }));
  };

  const toggleSector = (sector: string) => {
    setSavedFilters((prev) => ({
      ...prev,
      sectors: prev.sectors.includes(sector)
        ? prev.sectors.filter((s) => s !== sector)
        : [...prev.sectors, sector],
    }));
  };

  const toggleHorizon = (horizon: string) => {
    setSavedFilters((prev) => ({
      ...prev,
      horizons: prev.horizons.includes(horizon)
        ? prev.horizons.filter((h) => h !== horizon)
        : [...prev.horizons, horizon],
    }));
  };

  const handleSaveFilters = async () => {
    try {
      setSavingFilters(true);
      await fetch("/api/proxy/preferences/filters", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(savedFilters),
      });
      showToast("Filters saved successfully", "success");
    } catch (err) {
      showToast("Failed to save filters", "error");
    } finally {
      setSavingFilters(false);
    }
  };

  const handleDigestChange = async (frequency: string | null) => {
    try {
      setSavingDigest(true);

      if (frequency === null) {
        if (digest?.id) {
          await fetch(`/api/proxy/digests/${digest.id}`, {
            method: "DELETE",
          });
        }
        setDigest(null);
        showToast("Email digest disabled", "success");
      } else {
        const response = await fetch("/api/proxy/digests", {
          method: digest ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            frequency,
            delivery_time: "08:00",
            delivery_day: frequency === "weekly" ? 1 : null,
            active: true,
          }),
        });
        if (response.ok) {
          const data = await response.json();
          setDigest(data);
          showToast(`Email digest set to ${frequency}`, "success");
        } else {
          throw new Error("Failed to update digest");
        }
      }
    } catch (err) {
      showToast("Failed to update digest settings", "error");
    } finally {
      setSavingDigest(false);
    }
  };

  const handleExportEvents = async () => {
    try {
      setExporting(true);
      const response = await fetch("/api/proxy/export/events");
      if (!response.ok) throw new Error("Export failed");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `events_export_${new Date().toISOString().split("T")[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);

      showToast("Events exported successfully", "success");
    } catch (err) {
      showToast("Failed to export events", "error");
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-[--text]">Settings</h2>
        <p className="text-sm text-[--muted]">
          Configure your preferences, filters, and notification settings
        </p>
      </div>

      <div className="space-y-6 max-w-3xl">
        <section className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
            <Sun className="h-5 w-5 text-[--warning]" />
            Appearance
          </h3>
          <p className="text-sm text-[--muted] mb-4">
            Choose how Release Radar looks to you. Select a single theme or sync with your system settings.
          </p>
          <div className="flex gap-3 flex-wrap">
            {(["light", "dark", "system"] as const).map((t) => (
              <Button
                key={t}
                variant={theme === t ? "default" : "outline"}
                onClick={() => handleThemeChange(t)}
                disabled={savingTheme}
                className="flex items-center gap-2"
              >
                {t === "light" && <Sun className="h-4 w-4" />}
                {t === "dark" && <Moon className="h-4 w-4" />}
                {t === "system" && <Monitor className="h-4 w-4" />}
                {t.charAt(0).toUpperCase() + t.slice(1)}
                {theme === t && <Check className="h-3 w-3 ml-1" />}
              </Button>
            ))}
            {savingTheme && <Loader2 className="h-5 w-5 animate-spin text-[--muted]" />}
          </div>
        </section>

        <section className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
            <Filter className="h-5 w-5 text-[--primary]" />
            Saved Filters
          </h3>
          <p className="text-sm text-[--muted] mb-6">
            Set default filters that will be applied whenever you view events. These preferences persist across sessions.
          </p>

          <div className="space-y-6">
            <div>
              <h4 className="text-sm font-medium text-[--text] mb-3">Event Types</h4>
              <div className="flex flex-wrap gap-2">
                {EVENT_TYPES.map((type) => (
                  <button
                    key={type}
                    onClick={() => toggleEventType(type)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      savedFilters.event_types.includes(type)
                        ? "bg-[--tag-active-bg] text-[--tag-active-text] font-medium"
                        : "bg-[--tag-muted-bg] text-[--tag-muted-text] hover:bg-[--surface-hover] border border-[--tag-muted-border]"
                    }`}
                  >
                    {type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-[--text] mb-3">Sectors</h4>
              <div className="flex flex-wrap gap-2">
                {SECTORS.map((sector) => (
                  <button
                    key={sector}
                    onClick={() => toggleSector(sector)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      savedFilters.sectors.includes(sector)
                        ? "bg-[--tag-active-bg] text-[--tag-active-text] font-medium"
                        : "bg-[--tag-muted-bg] text-[--tag-muted-text] hover:bg-[--surface-hover] border border-[--tag-muted-border]"
                    }`}
                  >
                    {sector}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-[--text] mb-3">Time Horizons</h4>
              <div className="flex flex-wrap gap-2">
                {HORIZONS.map((horizon) => (
                  <button
                    key={horizon}
                    onClick={() => toggleHorizon(horizon)}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                      savedFilters.horizons.includes(horizon)
                        ? "bg-[--tag-active-bg] text-[--tag-active-text] font-medium"
                        : "bg-[--tag-muted-bg] text-[--tag-muted-text] hover:bg-[--surface-hover] border border-[--tag-muted-border]"
                    }`}
                  >
                    {horizon}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-[--text] mb-3">
                Minimum Impact Score: {savedFilters.min_score}
              </h4>
              <input
                type="range"
                min="0"
                max="100"
                value={savedFilters.min_score}
                onChange={(e) =>
                  setSavedFilters((prev) => ({
                    ...prev,
                    min_score: parseInt(e.target.value),
                  }))
                }
                className="w-full max-w-xs accent-[--primary]"
              />
              <div className="flex justify-between text-xs text-[--muted] max-w-xs mt-1">
                <span>0</span>
                <span>50</span>
                <span>100</span>
              </div>
            </div>

            <div className="pt-2">
              <Button
                onClick={handleSaveFilters}
                disabled={savingFilters}
                className="flex items-center gap-2"
              >
                {savingFilters ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save Filters
              </Button>
            </div>
          </div>
        </section>

        <section className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
            <Mail className="h-5 w-5 text-[--primary]" />
            Email Digests
          </h3>
          <p className="text-sm text-[--muted] mb-6">
            Receive a summary of important events directly in your inbox. Choose your preferred frequency.
          </p>

          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <span className="text-sm text-[--text]">Digest frequency</span>
              <div className="flex gap-2">
                <Button
                  variant={digest?.frequency === "daily" && digest?.active ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleDigestChange("daily")}
                  disabled={savingDigest}
                >
                  Daily
                </Button>
                <Button
                  variant={digest?.frequency === "weekly" && digest?.active ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleDigestChange("weekly")}
                  disabled={savingDigest}
                >
                  Weekly
                </Button>
                <Button
                  variant={!digest?.active ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleDigestChange(null)}
                  disabled={savingDigest}
                >
                  None
                </Button>
                {savingDigest && <Loader2 className="h-4 w-4 animate-spin text-[--muted]" />}
              </div>
            </div>

            {digest?.active && (
              <div className="rounded-lg bg-[--surface-muted] border border-[--border-muted] p-4">
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[--muted]">Status</span>
                    <span className="text-[--success]">Active</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[--muted]">Frequency</span>
                    <span className="text-[--text] capitalize">{digest.frequency}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[--muted]">Delivery time</span>
                    <span className="text-[--text]">{digest.delivery_time || "08:00"} UTC</span>
                  </div>
                  {digest.next_send_at && (
                    <div className="flex justify-between">
                      <span className="text-[--muted]">Next delivery</span>
                      <span className="text-[--text]">
                        {new Date(digest.next_send_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-[--border] bg-[--panel] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
            <Download className="h-5 w-5 text-[--success]" />
            Export Data
          </h3>
          <p className="text-sm text-[--muted] mb-4">
            Download your tracked events as a CSV file for external analysis or record-keeping.
          </p>
          <Button
            onClick={handleExportEvents}
            variant="outline"
            disabled={exporting}
            className="flex items-center gap-2"
          >
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Export Events as CSV
          </Button>
        </section>
      </div>
    </div>
  );
}
