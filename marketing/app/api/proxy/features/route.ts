/**
 * Feature flags proxy endpoint.
 * 
 * Fetches feature flags from backend and returns them to the frontend.
 * Falls back to all-disabled state if backend is unavailable.
 */

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/features`, {
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!res.ok) {
      return NextResponse.json({
        enableLiveWs: false,
        enableLabsUi: false,
        enableXSentiment: false,
        enableAlertsBeta: false,
        enableAdvancedAnalytics: false,
      });
    }
    
    const flags = await res.json();
    return NextResponse.json(flags);
  } catch {
    return NextResponse.json({
      enableLiveWs: false,
      enableLabsUi: false,
      enableXSentiment: false,
      enableAlertsBeta: false,
      enableAdvancedAnalytics: false,
    }, { status: 500 });
  }
}
