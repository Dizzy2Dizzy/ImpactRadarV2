import { create } from 'zustand';

export interface LiveEvent {
  id: number;
  ticker: string;
  headline: string;
  event_type: string;
  published_at: string;
  source_url: string | null;
  impact_score: number;
  direction: string | null;
  confidence: number;
  score?: number;
  computed_at?: string;
  receivedAt: number;
}

interface LiveEventsState {
  events: LiveEvent[];
  lastHeartbeat: string | null;
  isPaused: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error' | 'disabled';
  
  addEvent: (event: Omit<LiveEvent, 'receivedAt'>) => void;
  updateEventScore: (eventId: number, scoreData: {
    score: number;
    confidence: number;
    direction?: string;
    computed_at?: string;
  }) => void;
  setLastHeartbeat: (timestamp: string) => void;
  setConnectionState: (state: 'connecting' | 'connected' | 'disconnected' | 'error' | 'disabled') => void;
  togglePause: () => void;
  clearEvents: () => void;
}

export const useLiveEventsStore = create<LiveEventsState>((set) => ({
  events: [],
  lastHeartbeat: null,
  isPaused: false,
  connectionState: 'disconnected',
  
  addEvent: (event) =>
    set((state) => {
      if (state.isPaused) {
        return state;
      }
      
      const exists = state.events.some((e) => e.id === event.id);
      if (exists) {
        return state;
      }
      
      const newEvent: LiveEvent = {
        ...event,
        receivedAt: Date.now(),
      };
      
      const newEvents = [newEvent, ...state.events].slice(0, 100);
      return { events: newEvents };
    }),
  
  updateEventScore: (eventId, scoreData) =>
    set((state) => {
      const events = state.events.map((event) =>
        event.id === eventId
          ? {
              ...event,
              impact_score: scoreData.score,
              confidence: scoreData.confidence,
              direction: scoreData.direction || event.direction,
              computed_at: scoreData.computed_at,
            }
          : event
      );
      return { events };
    }),
  
  setLastHeartbeat: (timestamp) =>
    set({ lastHeartbeat: timestamp }),
  
  setConnectionState: (state) =>
    set({ connectionState: state }),
  
  togglePause: () =>
    set((state) => ({ isPaused: !state.isPaused })),
  
  clearEvents: () =>
    set({ events: [] }),
}));
