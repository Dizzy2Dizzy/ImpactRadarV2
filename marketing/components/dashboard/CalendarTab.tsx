'use client';

import { useState, useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Filter, X } from 'lucide-react';
import { CalendarDayModal } from './CalendarDayModal';
import { ModelVersionFilter } from './ModelVersionFilter';
import { DisplayVersion } from './ImpactScoreBadge';

interface Event {
  id: number;
  ticker: string;
  company_name: string;
  event_type: string;
  title: string;
  description?: string;
  date: string;
  source: string;
  source_url?: string;
  impact_score: number;
  direction: string;
  confidence: number;
  rationale?: string;
  sector?: string;
  info_tier?: string;
  info_subtype?: string;
  impact_p_move?: number;
  impact_p_up?: number;
  impact_p_down?: number;
  ml_adjusted_score?: number;
  ml_confidence?: number;
  model_source?: 'family-specific' | 'global' | 'deterministic';
  ml_model_version?: string;
}

interface CalendarData {
  year: number;
  month: number;
  events_by_date: Record<string, Event[]>;
  summary: {
    total_events: number;
    high_impact_days: string[];
  };
}

export function CalendarTab() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [showDayModal, setShowDayModal] = useState(false);
  
  // Filter state
  const [showFilters, setShowFilters] = useState(false);
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedEventTypes, setSelectedEventTypes] = useState<string[]>([]);
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1; // JavaScript months are 0-indexed

  useEffect(() => {
    loadCalendarData();
  }, [year, month, watchlistOnly]);

  const loadCalendarData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        year: year.toString(),
        month: month.toString(),
        watchlist_only: watchlistOnly.toString(),
      });

      const response = await fetch(`/api/proxy/events/calendar?${params.toString()}`);
      
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access not available, please upgrade plan');
        }
        const errorText = await response.text();
        console.error('Calendar API error:', errorText);
        throw new Error('Failed to load calendar data');
      }

      const data = await response.json();
      setCalendarData(data);
    } catch (err: any) {
      console.error('Failed to load calendar:', err);
      setError(err?.message || 'Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  };

  const goToPreviousMonth = () => {
    setCurrentDate(new Date(year, month - 2, 1));
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month, 1));
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const handleDateClick = (dateStr: string) => {
    setSelectedDate(dateStr);
    setShowDayModal(true);
  };

  const getDaysInMonth = (year: number, month: number) => {
    return new Date(year, month, 0).getDate();
  };

  const getFirstDayOfMonth = (year: number, month: number) => {
    return new Date(year, month - 1, 1).getDay(); // 0 = Sunday
  };

  const generateCalendarDays = () => {
    const daysInMonth = getDaysInMonth(year, month);
    const firstDay = getFirstDayOfMonth(year, month);
    const days: (number | null)[] = [];

    // Add empty cells for days before the first day of the month
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }

    // Add all days in the month
    for (let day = 1; day <= daysInMonth; day++) {
      days.push(day);
    }

    return days;
  };

  const getDateString = (day: number) => {
    return `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
  };

  // Extract unique companies and event types from calendar data
  const { availableCompanies, availableEventTypes } = useMemo(() => {
    if (!calendarData) return { availableCompanies: [], availableEventTypes: [] };
    
    const companies = new Set<string>();
    const eventTypes = new Set<string>();
    
    Object.values(calendarData.events_by_date).forEach(events => {
      events.forEach(event => {
        companies.add(event.company_name);
        eventTypes.add(event.event_type);
      });
    });
    
    return {
      availableCompanies: Array.from(companies).sort(),
      availableEventTypes: Array.from(eventTypes).sort()
    };
  }, [calendarData]);

  // Filter function
  const filterEvents = (events: Event[]): Event[] => {
    let filtered = events;
    
    // For V2.0 mode, only show events with ML scores
    if (modelVersion === 'v2.0') {
      filtered = filtered.filter(event => 
        event.model_source !== 'deterministic' && 
        event.ml_adjusted_score != null
      );
    }
    
    // Apply company and event type filters
    if (selectedCompanies.length > 0 || selectedEventTypes.length > 0) {
      filtered = filtered.filter(event => {
        const companyMatch = selectedCompanies.length === 0 || selectedCompanies.includes(event.company_name);
        const eventTypeMatch = selectedEventTypes.length === 0 || selectedEventTypes.includes(event.event_type);
        return companyMatch && eventTypeMatch;
      });
    }
    
    return filtered;
  };

  const getEventsForDate = (day: number): Event[] => {
    const dateStr = getDateString(day);
    const events = calendarData?.events_by_date[dateStr] || [];
    return filterEvents(events);
  };

  const toggleCompanyFilter = (company: string) => {
    setSelectedCompanies(prev =>
      prev.includes(company)
        ? prev.filter(c => c !== company)
        : [...prev, company]
    );
  };

  const toggleEventTypeFilter = (eventType: string) => {
    setSelectedEventTypes(prev =>
      prev.includes(eventType)
        ? prev.filter(t => t !== eventType)
        : [...prev, eventType]
    );
  };

  const clearFilters = () => {
    setSelectedCompanies([]);
    setSelectedEventTypes([]);
  };

  const hasActiveFilters = selectedCompanies.length > 0 || selectedEventTypes.length > 0;

  const getImpactColor = (events: Event[]): string => {
    if (events.length === 0) return '';
    
    const maxImpact = Math.max(...events.map(e => e.impact_score));
    const totalImpact = events.reduce((sum, e) => sum + e.impact_score, 0);

    if (maxImpact >= 75 || totalImpact >= 150) {
      return 'bg-[--success-soft] border-[--border-strong]';
    } else if (maxImpact >= 50 || totalImpact >= 100) {
      return 'bg-[--warning-soft] border-[--border-strong]';
    } else {
      return 'bg-[--muted-soft] border-[--border-strong]';
    }
  };

  const isHighImpactDay = (day: number): boolean => {
    const dateStr = getDateString(day);
    return calendarData?.summary.high_impact_days.includes(dateStr) || false;
  };

  const isToday = (day: number): boolean => {
    const today = new Date();
    return (
      day === today.getDate() &&
      month === today.getMonth() + 1 &&
      year === today.getFullYear()
    );
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  if (loading && !calendarData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading calendar...</p>
      </div>
    );
  }

  const calendarDays = generateCalendarDays();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Event Calendar</h2>
          <p className="text-sm text-[--muted]">
            {calendarData?.summary.total_events || 0} events in {monthNames[month - 1]}
            {hasActiveFilters && <span className="text-[--primary] ml-2">(Filtered)</span>}
          </p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
          <div className="flex gap-2">
            <Button
              onClick={() => setWatchlistOnly(!watchlistOnly)}
              variant={watchlistOnly ? 'default' : 'outline'}
              className="flex items-center gap-2"
            >
              <CalendarIcon className="h-4 w-4" />
              {watchlistOnly ? 'Watchlist Only' : 'All Events'}
            </Button>
            <Button
              onClick={() => setShowFilters(!showFilters)}
              variant={showFilters || hasActiveFilters ? 'default' : 'outline'}
              className="flex items-center gap-2"
            >
              <Filter className="h-4 w-4" />
              Filters
              {hasActiveFilters && (
                <span className="ml-1 px-1.5 py-0.5 bg-[--surface-hover] rounded text-xs">
                  {selectedCompanies.length + selectedEventTypes.length}
                </span>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-[--surface-muted] border border-[--border] rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-[--text]">Filters</h3>
            {hasActiveFilters && (
              <Button
                onClick={clearFilters}
                variant="ghost"
                size="sm"
                className="flex items-center gap-2"
              >
                <X className="h-4 w-4" />
                Clear All
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Companies Filter */}
            <div>
              <h4 className="text-sm font-semibold text-[--text] mb-2">
                Companies ({availableCompanies.length})
              </h4>
              <div className="max-h-60 overflow-y-auto space-y-2 border border-[--border] rounded-lg p-3 bg-[--surface-strong]">
                {availableCompanies.map(company => (
                  <label
                    key={company}
                    className="flex items-center gap-2 cursor-pointer hover:bg-[--surface-hover] p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selectedCompanies.includes(company)}
                      onChange={() => toggleCompanyFilter(company)}
                      className="rounded border-[--border-strong] text-[--primary] focus:ring-[--primary]"
                    />
                    <span className="text-sm text-[--text]">{company}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Event Types Filter */}
            <div>
              <h4 className="text-sm font-semibold text-[--text] mb-2">
                Event Types ({availableEventTypes.length})
              </h4>
              <div className="max-h-60 overflow-y-auto space-y-2 border border-[--border] rounded-lg p-3 bg-[--surface-strong]">
                {availableEventTypes.map(eventType => (
                  <label
                    key={eventType}
                    className="flex items-center gap-2 cursor-pointer hover:bg-[--surface-hover] p-2 rounded"
                  >
                    <input
                      type="checkbox"
                      checked={selectedEventTypes.includes(eventType)}
                      onChange={() => toggleEventTypeFilter(eventType)}
                      className="rounded border-[--border-strong] text-[--primary] focus:ring-[--primary]"
                    />
                    <span className="text-sm text-[--text] capitalize">
                      {eventType.replace(/_/g, ' ')}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
          <p className="text-[--error]">{error}</p>
          <Button onClick={() => loadCalendarData()} variant="outline" size="sm" className="mt-2">
            Retry
          </Button>
        </div>
      )}

      {/* Month Navigation */}
      <div className="flex items-center justify-between bg-[--surface-muted] rounded-lg p-4">
        <Button
          onClick={goToPreviousMonth}
          variant="ghost"
          size="sm"
          className="flex items-center gap-2"
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </Button>
        
        <div className="text-center">
          <h3 className="text-xl font-bold text-[--text]">
            {monthNames[month - 1]} {year}
          </h3>
          {calendarData?.summary.high_impact_days.length ? (
            <p className="text-sm text-[--warning] mt-1">
              {calendarData.summary.high_impact_days.length} high impact day
              {calendarData.summary.high_impact_days.length !== 1 ? 's' : ''}
            </p>
          ) : null}
        </div>
        
        <div className="flex gap-2">
          <Button
            onClick={goToToday}
            variant="outline"
            size="sm"
          >
            Today
          </Button>
          <Button
            onClick={goToNextMonth}
            variant="ghost"
            size="sm"
            className="flex items-center gap-2"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-[--surface-muted] rounded-lg p-4">
        {/* Day Headers */}
        <div className="grid grid-cols-7 gap-2 mb-2">
          {dayNames.map(day => (
            <div
              key={day}
              className="text-center text-sm font-semibold text-[--muted] py-2"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Days */}
        <div className="grid grid-cols-7 gap-2">
          {calendarDays.map((day, index) => {
            if (day === null) {
              return <div key={`empty-${index}`} className="aspect-square" />;
            }

            const events = getEventsForDate(day);
            const impactColor = getImpactColor(events);
            const isHigh = isHighImpactDay(day);
            const today = isToday(day);

            return (
              <button
                key={day}
                onClick={() => events.length > 0 && handleDateClick(getDateString(day))}
                disabled={events.length === 0}
                className={`
                  aspect-square p-2 rounded-lg border transition-all relative
                  ${events.length > 0 
                    ? `${impactColor} cursor-pointer hover:scale-105 hover:shadow-lg` 
                    : 'bg-[--surface-muted] border-[--border] cursor-default'
                  }
                  ${today ? 'ring-2 ring-[--primary]' : ''}
                `}
              >
                {/* Day Number */}
                <div className={`
                  text-sm font-semibold 
                  ${today ? 'text-[--primary]' : events.length > 0 ? 'text-[--text]' : 'text-[--muted]'}
                `}>
                  {day}
                </div>

                {/* Max Impact Score Badge */}
                {events.length > 0 && (
                  <div className="absolute top-1 right-1">
                    <span className={`
                      inline-flex items-center justify-center min-w-8 h-8 px-1.5 text-xs font-bold rounded-full
                      ${isHigh 
                        ? 'bg-[--success] text-[--text-on-primary]' 
                        : 'bg-[--primary] text-[--text-on-primary]'
                      }
                    `}>
                      {Math.max(...events.map(e => e.impact_score))}
                    </span>
                  </div>
                )}

                {/* Impact Indicator Dots */}
                {events.length > 0 && (
                  <div className="absolute bottom-1 left-0 right-0 flex justify-center gap-0.5">
                    {events.slice(0, 3).map((event, i) => {
                      let dotColor = 'bg-[--muted]';
                      if (event.impact_score >= 75) dotColor = 'bg-[--success]';
                      else if (event.impact_score >= 50) dotColor = 'bg-[--warning]';
                      else dotColor = 'bg-[--muted]';

                      return (
                        <div
                          key={i}
                          className={`h-1.5 w-1.5 rounded-full ${dotColor}`}
                        />
                      );
                    })}
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Empty State Message */}
      {calendarData && calendarData.summary.total_events === 0 && !loading && (
        <div className="bg-[--primary-light] border border-[--border] rounded-lg p-6 text-center">
          <CalendarIcon className="h-12 w-12 text-[--primary] mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-[--text] mb-2">No events for {monthNames[month - 1]} {year}</h3>
          <p className="text-[--muted] mb-4">
            Events are tracked as they are announced. Navigate to previous months to view historical events.
          </p>
          <Button
            onClick={goToPreviousMonth}
            variant="outline"
            className="flex items-center gap-2 mx-auto"
          >
            <ChevronLeft className="h-4 w-4" />
            View {monthNames[month - 2 >= 0 ? month - 2 : 11]} Events
          </Button>
        </div>
      )}

      {/* Legend */}
      <div className="bg-[--surface-muted] rounded-lg p-4">
        <h4 className="text-sm font-semibold text-[--text] mb-3">Impact Legend</h4>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-[--muted-soft] border border-[--border-strong]" />
            <div>
              <div className="text-sm font-medium text-[--text]">Low Impact</div>
              <div className="text-xs text-[--muted]">Score &lt; 50</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-[--warning-soft] border border-[--border-strong]" />
            <div>
              <div className="text-sm font-medium text-[--text]">Medium Impact</div>
              <div className="text-xs text-[--muted]">Score 50-74</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-[--success-soft] border border-[--border-strong]" />
            <div>
              <div className="text-sm font-medium text-[--text]">High Impact</div>
              <div className="text-xs text-[--muted]">Score ≥ 75</div>
            </div>
          </div>
        </div>
      </div>

      {/* Day Modal */}
      {selectedDate && (
        <CalendarDayModal
          open={showDayModal}
          onClose={() => setShowDayModal(false)}
          date={selectedDate}
          events={filterEvents(calendarData?.events_by_date[selectedDate] || [])}
          displayVersion={modelVersion}
        />
      )}
    </div>
  );
}
