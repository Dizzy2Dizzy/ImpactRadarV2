import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { logger } from "@/lib/logger";

export async function GET() {
  try {
    const session = await getSession();

    if (!session) {
      return NextResponse.json({ isLoggedIn: false }, { status: 200 });
    }

    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.id, session.userId))
      .limit(1);

    if (!user) {
      return NextResponse.json({ isLoggedIn: false }, { status: 200 });
    }

    return NextResponse.json(
      {
        isLoggedIn: true,
        plan: user.plan || "free",
        email: user.email,
        isVerified: user.isVerified || false,
      },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Auth check error", { error });
    return NextResponse.json({ isLoggedIn: false }, { status: 200 });
  }
}
