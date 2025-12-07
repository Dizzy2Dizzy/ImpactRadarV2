import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { generateResetToken, hashToken, storeResetToken, getLastResetRequestTime } from "@/lib/password-reset";
import { sendPasswordResetEmail } from "@/lib/email";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email) {
      return NextResponse.json(
        { error: "Email is required" },
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
        { success: true, message: "If an account exists with this email, you will receive a password reset link shortly." },
        { status: 200 }
      );
    }

    const lastRequestTime = await getLastResetRequestTime(email);
    if (lastRequestTime) {
      const timeSinceLastRequest = Date.now() - lastRequestTime.getTime();
      const minWaitTime = 60 * 1000;
      
      if (timeSinceLastRequest < minWaitTime) {
        const secondsRemaining = Math.ceil((minWaitTime - timeSinceLastRequest) / 1000);
        return NextResponse.json(
          { error: `Please wait ${secondsRemaining} seconds before requesting another reset link.` },
          { status: 429 }
        );
      }
    }

    const resetToken = generateResetToken();
    const tokenHash = await hashToken(resetToken);
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + 1);

    await storeResetToken(user.id, tokenHash, expiresAt);

    try {
      await sendPasswordResetEmail(email, resetToken);
      logger.info("Password reset email sent successfully", { email });
    } catch (emailError) {
      logger.error("Failed to send password reset email", { email, error: emailError });
      return NextResponse.json(
        { error: "Failed to send reset email. Please try again later." },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { success: true, message: "If an account exists with this email, you will receive a password reset link shortly." },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Forgot password error", { error });
    return NextResponse.json(
      { error: "Failed to process password reset request" },
      { status: 500 }
    );
  }
}
