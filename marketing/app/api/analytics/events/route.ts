import { NextResponse } from "next/server";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const { events } = await request.json();

    if (!Array.isArray(events)) {
      return NextResponse.json(
        { error: "Invalid events payload" },
        { status: 400 }
      );
    }

    logger.info("Analytics events received", {
      count: events.length,
      events: events.map(e => ({ name: e.name, timestamp: e.timestamp })),
    });

    // In production, you could send these to:
    // - PostHog
    // - Mixpanel
    // - Amplitude
    // - Your own analytics database
    
    // For now, just acknowledge receipt
    return NextResponse.json({ success: true, received: events.length });
  } catch (error) {
    logger.error("Analytics events error", { error });
    return NextResponse.json(
      { error: "Failed to process events" },
      { status: 500 }
    );
  }
}
