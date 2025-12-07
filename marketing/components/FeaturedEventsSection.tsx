'use client';

import { useState } from 'react';
import { EventCard } from './EventCard';
import { PriceChartModal } from './dashboard/PriceChartModal';

interface FeaturedEvent {
  id: number;
  title: string;
  company: string;
  date: string;
  category: string;
  score: number;
  direction: "positive" | "negative" | "neutral";
  sourceUrl: string;
  rawDate?: string;
}

interface FeaturedEventsSectionProps {
  events: FeaturedEvent[];
}

export function FeaturedEventsSection({ events }: FeaturedEventsSectionProps) {
  const [showChart, setShowChart] = useState(false);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [selectedEventDate, setSelectedEventDate] = useState('');

  const handleEventClick = (event: FeaturedEvent) => {
    setSelectedTicker(event.company);
    setSelectedEventDate(event.rawDate || event.date);
    setShowChart(true);
  };

  if (events.length === 0) {
    return (
      <div className="col-span-full text-center py-12">
        <p className="text-[--muted] mb-4">
          Events from our scanners will appear here once they start collecting data.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {events.map((event, i) => (
          <div
            key={event.id || i}
            onClick={() => handleEventClick(event)}
            className="cursor-pointer block transition-transform hover:scale-105"
          >
            <EventCard {...event} />
          </div>
        ))}
      </div>

      <PriceChartModal
        open={showChart}
        onClose={() => setShowChart(false)}
        ticker={selectedTicker}
        initialDays={90}
        focusEventDate={selectedEventDate}
      />
    </>
  );
}
