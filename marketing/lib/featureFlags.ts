/**
 * Feature flags for controlling V1 vs Beta/Labs features.
 * 
 * Supports both client-side (Next.js env) and server-side (backend API) flags.
 * Falls back to client flags if backend is unavailable.
 */

export interface FeatureFlags {
  enableLiveWs: boolean;
  enableLabsUi: boolean;
  enableXSentiment: boolean;
  enableAlertsBeta: boolean;
  enableAdvancedAnalytics: boolean;
}

// Client-side flags from env (fallback)
export const clientFeatureFlags: FeatureFlags = {
  enableLiveWs: process.env.NEXT_PUBLIC_ENABLE_LIVE_WS === 'true',
  enableLabsUi: process.env.NEXT_PUBLIC_ENABLE_LABS_UI === 'true',
  enableXSentiment: process.env.NEXT_PUBLIC_ENABLE_X_SENTIMENT === 'true',
  enableAlertsBeta: process.env.NEXT_PUBLIC_ENABLE_ALERTS_BETA === 'true',
  enableAdvancedAnalytics: process.env.NEXT_PUBLIC_ENABLE_ADVANCED_ANALYTICS === 'true',
};

// Fetch server flags
export async function getServerFeatureFlags(): Promise<FeatureFlags> {
  try {
    const res = await fetch('/api/proxy/features');
    if (!res.ok) return clientFeatureFlags;
    return await res.json();
  } catch {
    return clientFeatureFlags;
  }
}
