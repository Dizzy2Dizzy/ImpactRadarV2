import { NextResponse } from "next/server";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const errorData = await request.json();

    logger.error("Client error reported", {
      message: errorData.message,
      url: errorData.url,
      timestamp: new Date(errorData.timestamp).toISOString(),
      stack: errorData.stack?.substring(0, 500),
    });

    // In production, you could:
    // 1. Send to Sentry
    // 2. Store in database for analysis
    // 3. Alert on critical errors
    // 4. Send to log aggregation service (DataDog, LogRocket, etc.)

    return NextResponse.json({ success: true });
  } catch (error) {
    logger.error("Error logging endpoint failed", { error });
    return NextResponse.json(
      { error: "Failed to log error" },
      { status: 500 }
    );
  }
}
