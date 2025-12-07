import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { createSession } from "@/lib/auth";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  // Only allow in development/test environments
  if (process.env.NODE_ENV === "production") {
    return NextResponse.json(
      { error: "Not available in production" },
      { status: 403 }
    );
  }

  try {
    const body = await request.json();
    const { email } = body;

    if (!email || !email.includes('test_e2e_')) {
      return NextResponse.json(
        { error: "Only test emails allowed" },
        { status: 400 }
      );
    }

    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.email, email))
      .limit(1);

    if (!user) {
      return NextResponse.json(
        { error: "User not found" },
        { status: 404 }
      );
    }

    await db
      .update(users)
      .set({ isVerified: true })
      .where(eq(users.id, user.id));

    await createSession(user.id, true);

    return NextResponse.json(
      { success: true, message: "User verified" },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Test verification error", { error });
    return NextResponse.json(
      { error: "Failed to verify test user" },
      { status: 500 }
    );
  }
}
