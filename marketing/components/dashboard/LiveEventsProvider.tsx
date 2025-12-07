'use client';

import { createContext, useContext, ReactNode, useEffect } from 'react';
import { useLiveEvents } from '../../hooks/useLiveEvents';

interface LiveEventsContextValue {
  token: string | null;
}

const LiveEventsContext = createContext<LiveEventsContextValue>({ token: null });

export function useLiveEventsContext() {
  return useContext(LiveEventsContext);
}

interface LiveEventsProviderProps {
  children: ReactNode;
  token: string | null;
}

export function LiveEventsProvider({ children, token }: LiveEventsProviderProps) {
  useLiveEvents(token);
  
  return (
    <LiveEventsContext.Provider value={{ token }}>
      {children}
    </LiveEventsContext.Provider>
  );
}
