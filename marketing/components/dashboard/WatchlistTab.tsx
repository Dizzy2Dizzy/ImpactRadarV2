"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Trash2, Calendar } from "lucide-react";

interface WatchlistItem {
  ticker: string;
  company_name: string;
  company_id: number;
  sector: string;
  notes?: string;
  upcoming_events: any[];
}

export function WatchlistTab() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTicker, setNewTicker] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const response = await fetch("/api/proxy/watchlist");
      if (response.ok) {
        const data = await response.json();
        setWatchlist(data);
        setError(null);
      } else {
        setError("Failed to load watchlist. Please try again.");
      }
    } catch (error) {
      console.error("Failed to fetch watchlist:", error);
      setError("Network error. Please check your connection.");
    } finally {
      setLoading(false);
    }
  };

  const addToWatchlist = async () => {
    if (!newTicker.trim()) {
      setError("Please enter a ticker symbol");
      return;
    }

    setAdding(true);
    setError(null);

    try {
      // First find the company ID
      const companiesRes = await fetch(`/api/proxy/companies?q=${newTicker.trim()}&limit=1`);
      
      if (!companiesRes.ok) {
        if (companiesRes.status === 401) {
          setError("Please log in to add companies to your watchlist");
        } else {
          setError("Failed to search for company. Please try again.");
        }
        setAdding(false);
        return;
      }
      
      const companies = await companiesRes.json();
      if (companies.length === 0) {
        setError(`Company "${newTicker}" not found. Please check the ticker symbol.`);
        setAdding(false);
        return;
      }

      const company = companies[0];
      const response = await fetch("/api/proxy/watchlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_id: company.id,
          notes: newNotes.trim() || null
        })
      });

      if (response.ok) {
        setNewTicker("");
        setNewNotes("");
        setShowAddForm(false);
        setError(null);
        fetchWatchlist();
      } else if (response.status === 401) {
        setError("Please log in to add companies to your watchlist");
      } else if (response.status === 409) {
        setError("This company is already in your watchlist");
      } else {
        const errorData = await response.json().catch(() => null);
        setError(errorData?.detail || "Failed to add company. Please try again.");
      }
    } catch (error) {
      console.error("Failed to add to watchlist:", error);
      setError("Network error. Please check your connection and try again.");
    } finally {
      setAdding(false);
    }
  };

  const removeFromWatchlist = async (ticker: string, companyId: number) => {
    setError(null);
    
    try {
      const response = await fetch(`/api/proxy/watchlist/${companyId}`, {
        method: "DELETE"
      });

      if (response.ok) {
        fetchWatchlist();
      } else if (response.status === 401) {
        setError("Please log in to manage your watchlist");
      } else {
        setError("Failed to remove company. Please try again.");
      }
    } catch (error) {
      console.error("Failed to remove from watchlist:", error);
      setError("Network error. Please try again.");
    }
  };

  const groupWatchlistAlphabetically = (items: WatchlistItem[]) => {
    const sorted = [...items].sort((a, b) => a.ticker.localeCompare(b.ticker));
    const grouped: Record<string, WatchlistItem[]> = {};
    
    sorted.forEach(item => {
      const firstChar = item.ticker[0].toUpperCase();
      const groupKey = /[A-Z]/.test(firstChar) ? firstChar : '#';
      
      if (!grouped[groupKey]) {
        grouped[groupKey] = [];
      }
      grouped[groupKey].push(item);
    });
    
    return grouped;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-[--muted]">Loading watchlist...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-semibold text-[--text]">Watchlist</h2>
          <p className="text-sm text-[--muted]">Companies you're tracking</p>
        </div>
        <Button onClick={() => { setShowAddForm(!showAddForm); setError(null); }}>
          <Plus className="h-4 w-4 mr-2" />
          Add Company
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <p className="text-sm text-[--error]">{error}</p>
        </div>
      )}

      {/* Add Form */}
      {showAddForm && (
        <div className="rounded-lg border border-[--border] bg-[--panel] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4">Add to Watchlist</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-[--muted] mb-2">Ticker Symbol</label>
              <input
                type="text"
                placeholder="e.g., MRNA, NVDA"
                value={newTicker}
                onChange={(e) => { setNewTicker(e.target.value.toUpperCase()); setError(null); }}
                className="w-full rounded-lg border border-[--border] bg-[--bg] px-4 py-2 text-[--text]"
                disabled={adding}
              />
            </div>
            <div>
              <label className="block text-sm text-[--muted] mb-2">Notes (optional)</label>
              <textarea
                placeholder="Why are you watching this company?"
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-[--border] bg-[--bg] px-4 py-2 text-[--text]"
                disabled={adding}
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={addToWatchlist} className="flex-1" disabled={adding}>
                {adding ? "Adding..." : "Add to Watchlist"}
              </Button>
              <Button onClick={() => { setShowAddForm(false); setError(null); }} variant="outline" className="flex-1" disabled={adding}>
                Cancel
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Watchlist Items */}
      {watchlist.length === 0 ? (
        <div className="rounded-lg border border-[--border] bg-[--panel] p-12 text-center">
          <p className="text-[--muted] mb-4">Your watchlist is empty</p>
          <Button onClick={() => setShowAddForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Your First Company
          </Button>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(groupWatchlistAlphabetically(watchlist))
            .sort(([a], [b]) => {
              if (a === '#') return 1;
              if (b === '#') return -1;
              return a.localeCompare(b);
            })
            .map(([letter, items]) => (
              <div key={letter} className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-[--primary-soft] border border-[--border-strong]">
                    <span className="text-xl font-bold text-[--primary]">{letter}</span>
                  </div>
                  <div className="flex-1 h-px bg-[--border]"></div>
                </div>
                
                <div className="grid grid-cols-1 gap-4">
                  {items.map((item, idx) => (
                    <div key={idx} className="rounded-lg border border-[--border] bg-[--panel] p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-xl font-semibold text-[--text]">{item.ticker}</h3>
                          <p className="text-sm text-[--muted]">{item.company_name}</p>
                          <span className="inline-block mt-2 px-3 py-1 rounded-full text-xs bg-[--primary-light] text-[--primary]">
                            {item.sector}
                          </span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFromWatchlist(item.ticker, item.company_id)}
                          className="text-[--error] hover:text-[--error]"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>

                      {item.notes && (
                        <div className="mb-4 p-3 rounded-lg bg-[--bg] border border-[--border-muted]">
                          <p className="text-sm text-[--muted]">{item.notes}</p>
                        </div>
                      )}

                      {/* Upcoming Events */}
                      {item.upcoming_events && item.upcoming_events.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 text-sm text-[--muted] mb-3">
                            <Calendar className="h-4 w-4" />
                            <span>Upcoming Events ({item.upcoming_events.length})</span>
                          </div>
                          <div className="space-y-2">
                            {item.upcoming_events.slice(0, 3).map((event: any, eventIdx: number) => (
                              <div key={eventIdx} className="p-3 rounded-lg bg-[--bg] border border-[--border-muted]">
                                <div className="flex justify-between items-start text-sm">
                                  <span className="text-[--text]">{event.title}</span>
                                  <span className="text-[--muted]">
                                    {new Date(event.date).toLocaleDateString()}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
