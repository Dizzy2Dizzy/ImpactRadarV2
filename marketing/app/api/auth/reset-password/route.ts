import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { validateResetToken } from "@/lib/password-reset";
import { hashPassword } from "@/lib/auth";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, token, newPassword } = body;

    if (!email || !token || !newPassword) {
      return NextResponse.json(
        { error: "Email, token, and new password are required" },
        { status: 400 }
      );
    }

    if (newPassword.length < 8) {
      return NextResponse.json(
        { error: "Password must be at least 8 characters long" },
        { status: 400 }
      );
    }

    const validation = await validateResetToken(token, email);

    if (!validation.success) {
      return NextResponse.json(
        { error: validation.error || "Invalid or expired reset token" },
        { status: 400 }
      );
    }

    const hashedPassword = await hashPassword(newPassword);

    await db
      .update(users)
      .set({ 
        passwordHash: hashedPassword,
        lastLogin: new Date()
      })
      .where(eq(users.id, validation.userId!));

    logger.info("Password successfully reset", { userId: validation.userId });

    return NextResponse.json(
      { success: true, message: "Password has been reset successfully. You can now log in with your new password." },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Reset password error", { error });
    return NextResponse.json(
      { error: "Failed to reset password" },
      { status: 500 }
    );
  }
}
