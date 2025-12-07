"use client";

import { useState, useEffect } from "react";
import { Book, Target, StopCircle, Clock, TrendingUp, ChevronRight, ArrowLeft, Image, Search, Filter, Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PlaybookRule {
  id: number;
  rule_type: string;
  operator: string;
  value: any;
  is_required: boolean;
  weight: number;
}

interface PlaybookScreenshot {
  id: number;
  slot_index: number;
  image_url: string | null;
  caption: string | null;
  event_ref: number | null;
}

interface Playbook {
  id: number;
  slug: string;
  title: string;
  category: string;
  description: string | null;
  setup_conditions: Record<string, any>;
  entry_logic: string;
  stop_template: string | null;
  target_template: string | null;
  holding_period: string | null;
  win_rate: number | null;
  avg_r: number | null;
  sample_size: number;
  stats_metadata: Record<string, any> | null;
  display_order: number;
  is_active: boolean;
  is_featured: boolean;
  visibility: string;
  screenshots: PlaybookScreenshot[];
  rules: PlaybookRule[];
  created_at: string;
  updated_at: string | null;
}

interface MatchedEvent {
  match_id: number;
  event_id: number;
  confidence: number;
  match_source: string;
  event: {
    id: number;
    ticker: string;
    title: string;
    event_type: string;
    date: string;
    impact_score: number;
    direction: string;
    realized_return_1d: number | null;
  } | null;
}

const CATEGORY_COLORS: Record<string, string> = {
  earnings: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  fda: "bg-green-500/10 text-green-400 border-green-500/30",
  sec: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  corporate: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  default: "bg-slate-500/10 text-slate-400 border-slate-500/30",
};

export function PlaybooksTab() {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState<Playbook | null>(null);
  const [matchedEvents, setMatchedEvents] = useState<MatchedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    loadPlaybooks();
    loadCategories();
  }, []);

  useEffect(() => {
    if (selectedPlaybook) {
      loadMatchedEvents(selectedPlaybook.id);
    }
  }, [selectedPlaybook]);

  const loadPlaybooks = async () => {
    try {
      setLoading(true);
      setError(null);
      const url = new URL("/api/proxy/playbooks", window.location.origin);
      if (filterCategory) {
        url.searchParams.set("category", filterCategory);
      }
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setPlaybooks(Array.isArray(data) ? data : []);
      } else {
        setPlaybooks([]);
        if (res.status !== 404) {
          setError("Failed to load playbooks");
        }
      }
    } catch (err: any) {
      console.error("Error loading playbooks:", err);
      setPlaybooks([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const res = await fetch("/api/proxy/playbooks/categories");
      if (res.ok) {
        const data = await res.json();
        setCategories(data.categories || []);
      }
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  };

  const loadMatchedEvents = async (playbookId: number) => {
    try {
      setLoadingEvents(true);
      const res = await fetch(`/api/proxy/playbooks/${playbookId}/matches`);
      if (res.ok) {
        const data = await res.json();
        setMatchedEvents(Array.isArray(data) ? data : []);
      } else {
        setMatchedEvents([]);
      }
    } catch (err) {
      console.error("Error loading matched events:", err);
      setMatchedEvents([]);
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    loadPlaybooks();
  }, [filterCategory]);

  const filteredPlaybooks = playbooks.filter((pb) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      pb.title.toLowerCase().includes(query) ||
      pb.description?.toLowerCase().includes(query) ||
      pb.category.toLowerCase().includes(query)
    );
  });

  const getCategoryColor = (category: string) => {
    return CATEGORY_COLORS[category] || CATEGORY_COLORS.default;
  };

  const formatPercentage = (value: number | null) => {
    if (value === null || value === undefined) return "N/A";
    return `${(value * 100).toFixed(0)}%`;
  };

  const formatRatio = (value: number | null) => {
    if (value === null || value === undefined) return "N/A";
    return value.toFixed(1) + "R";
  };

  if (selectedPlaybook) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedPlaybook(null);
              setMatchedEvents([]);
            }}
            className="text-slate-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back to Library
          </Button>
        </div>

        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getCategoryColor(selectedPlaybook.category)}`}>
                  {selectedPlaybook.category.toUpperCase()}
                </span>
                {selectedPlaybook.is_featured && (
                  <span className="px-2 py-1 rounded text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
                    FEATURED
                  </span>
                )}
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">{selectedPlaybook.title}</h2>
              {selectedPlaybook.description && (
                <p className="text-slate-400 max-w-2xl">{selectedPlaybook.description}</p>
              )}
            </div>
            <div className="flex items-center gap-4">
              {selectedPlaybook.win_rate !== null && (
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-400">
                    {formatPercentage(selectedPlaybook.win_rate)}
                  </div>
                  <div className="text-xs text-slate-500">Win Rate</div>
                </div>
              )}
              {selectedPlaybook.avg_r !== null && (
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-400">
                    {formatRatio(selectedPlaybook.avg_r)}
                  </div>
                  <div className="text-xs text-slate-500">Avg R</div>
                </div>
              )}
              {selectedPlaybook.sample_size > 0 && (
                <div className="text-center">
                  <div className="text-2xl font-bold text-slate-300">
                    {selectedPlaybook.sample_size}
                  </div>
                  <div className="text-xs text-slate-500">Trades</div>
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <TrendingUp className="h-4 w-4" />
                <span className="text-sm font-medium">Entry Logic</span>
              </div>
              <p className="text-white text-sm">{selectedPlaybook.entry_logic}</p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <StopCircle className="h-4 w-4 text-red-400" />
                <span className="text-sm font-medium">Stop Template</span>
              </div>
              <p className="text-white text-sm">{selectedPlaybook.stop_template || "Not specified"}</p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Target className="h-4 w-4 text-green-400" />
                <span className="text-sm font-medium">Target Template</span>
              </div>
              <p className="text-white text-sm">{selectedPlaybook.target_template || "Not specified"}</p>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="flex items-center gap-2 text-slate-400 mb-2">
                <Clock className="h-4 w-4" />
                <span className="text-sm font-medium">Holding Period</span>
              </div>
              <p className="text-white text-sm">{selectedPlaybook.holding_period || "Variable"}</p>
            </div>
          </div>

          {selectedPlaybook.setup_conditions && Object.keys(selectedPlaybook.setup_conditions).length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-white mb-3">Setup Conditions</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(selectedPlaybook.setup_conditions).map(([key, value]) => (
                  <span key={key} className="px-3 py-1 bg-slate-700/50 rounded-full text-sm text-slate-300">
                    {key}: {String(value)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {selectedPlaybook.rules && selectedPlaybook.rules.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-white mb-3">Matching Rules</h3>
              <div className="space-y-2">
                {selectedPlaybook.rules.map((rule) => (
                  <div key={rule.id} className="flex items-center gap-3 text-sm">
                    <span className={`w-2 h-2 rounded-full ${rule.is_required ? "bg-red-400" : "bg-slate-500"}`} />
                    <span className="text-slate-400">{rule.rule_type}:</span>
                    <span className="text-white">{rule.operator}</span>
                    <span className="text-blue-400">{JSON.stringify(rule.value)}</span>
                    {rule.is_required && <span className="text-xs text-red-400">(required)</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedPlaybook.screenshots && selectedPlaybook.screenshots.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-white mb-3">Screenshots</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {selectedPlaybook.screenshots.map((ss) => (
                  <div key={ss.id} className="bg-slate-900/50 rounded-lg overflow-hidden">
                    {ss.image_url ? (
                      <img src={ss.image_url} alt={ss.caption || "Screenshot"} className="w-full h-48 object-cover" />
                    ) : (
                      <div className="w-full h-48 flex items-center justify-center bg-slate-800">
                        <Image className="h-12 w-12 text-slate-600" />
                      </div>
                    )}
                    {ss.caption && (
                      <div className="p-3 text-sm text-slate-400">{ss.caption}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Matching Events</h3>
          {loadingEvents ? (
            <div className="text-slate-400 text-center py-8">Loading matched events...</div>
          ) : matchedEvents.length === 0 ? (
            <div className="text-slate-400 text-center py-8">No matching events found for this playbook.</div>
          ) : (
            <div className="space-y-3">
              {matchedEvents.slice(0, 10).map((match) => (
                <div
                  key={match.match_id}
                  className="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg hover:bg-slate-700/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <span className="font-mono font-bold text-blue-400">{match.event?.ticker || "N/A"}</span>
                    <span className="text-slate-300 truncate max-w-md">{match.event?.title || "Unknown event"}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-slate-500">{match.event?.date?.split("T")[0]}</span>
                    {match.event?.realized_return_1d !== null && (
                      <span className={`text-sm font-medium ${match.event!.realized_return_1d! > 0 ? "text-green-400" : "text-red-400"}`}>
                        {match.event!.realized_return_1d! > 0 ? "+" : ""}{match.event!.realized_return_1d!.toFixed(2)}%
                      </span>
                    )}
                    <span className="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">
                      {(match.confidence * 100).toFixed(0)}% match
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Book className="h-6 w-6 text-blue-400" />
            Playbook Library
          </h2>
          <p className="text-slate-400 mt-1">Trading strategy templates that auto-match to market events</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search playbooks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-slate-500" />
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="text-slate-400 text-center py-12">Loading playbooks...</div>
      ) : error ? (
        <div className="text-red-400 text-center py-12">{error}</div>
      ) : filteredPlaybooks.length === 0 ? (
        <div className="text-center py-12">
          <Book className="h-12 w-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400">No playbooks found. {searchQuery && "Try adjusting your search."}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPlaybooks.map((playbook) => (
            <div
              key={playbook.id}
              onClick={() => setSelectedPlaybook(playbook)}
              className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5 hover:border-blue-500/50 hover:bg-slate-800 transition-all cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-3">
                <span className={`px-2 py-1 rounded text-xs font-medium border ${getCategoryColor(playbook.category)}`}>
                  {playbook.category.toUpperCase()}
                </span>
                {playbook.is_featured && (
                  <Bookmark className="h-4 w-4 text-yellow-400" />
                )}
              </div>

              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
                {playbook.title}
              </h3>

              {playbook.description && (
                <p className="text-slate-400 text-sm mb-4 line-clamp-2">{playbook.description}</p>
              )}

              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  {playbook.win_rate !== null && (
                    <div className="text-center">
                      <div className="font-semibold text-green-400">{formatPercentage(playbook.win_rate)}</div>
                      <div className="text-xs text-slate-500">Win Rate</div>
                    </div>
                  )}
                  {playbook.avg_r !== null && (
                    <div className="text-center">
                      <div className="font-semibold text-blue-400">{formatRatio(playbook.avg_r)}</div>
                      <div className="text-xs text-slate-500">Avg R</div>
                    </div>
                  )}
                  {playbook.sample_size > 0 && (
                    <div className="text-center">
                      <div className="font-semibold text-slate-300">{playbook.sample_size}</div>
                      <div className="text-xs text-slate-500">Trades</div>
                    </div>
                  )}
                </div>
                <ChevronRight className="h-5 w-5 text-slate-600 group-hover:text-blue-400 transition-colors" />
              </div>

              {playbook.holding_period && (
                <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center gap-2 text-xs text-slate-500">
                  <Clock className="h-3 w-3" />
                  {playbook.holding_period}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
