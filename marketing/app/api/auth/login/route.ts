import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { verifyPassword, createSession } from "@/lib/auth";
import { eq } from "drizzle-orm";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, password } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required" },
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
        { error: "Invalid credentials" },
        { status: 401 }
      );
    }

    const isValidPassword = await verifyPassword(password, user.passwordHash);
    if (!isValidPassword) {
      return NextResponse.json(
        { error: "Invalid credentials" },
        { status: 401 }
      );
    }

    await createSession(user.id, user.isVerified || false);

    return NextResponse.json(
      { success: true, user: { id: user.id, email: user.email } },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Login failed", { error: String(error) });
    return NextResponse.json({ error: "Failed to login" }, { status: 500 });
  }
}
