import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { db } from "@/lib/db";
import { users, watchlist } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { logger } from "@/lib/logger";

export async function GET(request: Request) {
  try {
    const session = await getSession();

    if (!session) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.id, session.userId))
      .limit(1);

    if (!user) {
      return NextResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }

    const userWatchlists = await db
      .select()
      .from(watchlist)
      .where(eq(watchlist.userId, session.userId));

    const exportData = {
      exportDate: new Date().toISOString(),
      dataType: "Personal Data Export (GDPR Compliant)",
      user: {
        id: user.id,
        email: user.email,
        isVerified: user.isVerified,
        plan: user.plan,
        createdAt: user.createdAt,
        lastLogin: user.lastLogin,
      },
      watchlists: userWatchlists.map((w) => ({
        id: w.id,
        ticker: w.ticker,
        addedAt: w.createdAt,
      })),
      dataRetention: {
        notice: "You have the right to request deletion of your personal data at any time. To exercise this right, please visit your account settings or contact privacy@impactradar.co.",
      },
      privacyRights: {
        access: "You have the right to access your personal data (this export).",
        rectification: "You have the right to correct inaccurate personal data through your account settings.",
        erasure: "You have the right to request deletion of your personal data.",
        portability: "You have the right to receive your personal data in a structured, machine-readable format (this JSON export).",
        restriction: "You have the right to request restriction of processing of your personal data.",
        objection: "You have the right to object to processing of your personal data.",
        contact: "To exercise these rights, contact privacy@impactradar.co.",
      },
    };

    const jsonResponse = JSON.stringify(exportData, null, 2);

    return new NextResponse(jsonResponse, {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `attachment; filename="impact-radar-data-export-${user.id}-${Date.now()}.json"`,
      },
    });
  } catch (error) {
    logger.error("Data export error", { error });
    return NextResponse.json(
      { error: "Failed to export data" },
      { status: 500 }
    );
  }
}
