import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { emailWaitlist } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email || !email.includes("@")) {
      return NextResponse.json(
        { error: "Valid email is required" },
        { status: 400 }
      );
    }

    const existing = await db
      .select()
      .from(emailWaitlist)
      .where(eq(emailWaitlist.email, email))
      .limit(1);

    if (existing.length > 0) {
      return NextResponse.json(
        { error: "You're already on the waitlist!" },
        { status: 400 }
      );
    }

    await db.insert(emailWaitlist).values({ email });

    return NextResponse.json(
      { success: true, message: "Successfully joined the waitlist!" },
      { status: 201 }
    );
  } catch (error) {
    logger.error("Waitlist error", { error });
    return NextResponse.json(
      { error: "Failed to join waitlist" },
      { status: 500 }
    );
  }
}
