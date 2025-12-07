import { create } from 'zustand';

export type DashboardMode = 'watchlist' | 'portfolio';

interface DashboardModeState {
  mode: DashboardMode;
  isLoading: boolean;
  error: string | null;
  
  setMode: (mode: DashboardMode) => Promise<void>;
  fetchMode: () => Promise<void>;
}

export const useDashboardModeStore = create<DashboardModeState>((set, get) => ({
  mode: 'watchlist',
  isLoading: false,
  error: null,
  
  fetchMode: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch('/api/proxy/preferences/dashboard-mode', {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch dashboard mode');
      }
      
      const data = await response.json();
      set({ mode: data.mode, isLoading: false });
    } catch (error) {
      console.error('Error fetching dashboard mode:', error);
      set({ isLoading: false, error: 'Failed to load dashboard mode' });
    }
  },
  
  setMode: async (mode: DashboardMode) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch('/api/proxy/preferences/dashboard-mode', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ mode }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update dashboard mode');
      }
      
      set({ mode, isLoading: false });
    } catch (error) {
      console.error('Error updating dashboard mode:', error);
      set({ isLoading: false, error: 'Failed to update dashboard mode' });
    }
  },
}));
