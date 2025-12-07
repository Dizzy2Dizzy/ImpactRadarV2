import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import { generateVerificationCode, hashCode, storeVerificationCode, getLastCodeSentTime } from "@/lib/verification";
import { sendVerificationEmail } from "@/lib/email";
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
        { error: "User not found" },
        { status: 404 }
      );
    }

    if (user.isVerified) {
      return NextResponse.json(
        { error: "Email already verified" },
        { status: 400 }
      );
    }

    const lastCodeSent = await getLastCodeSentTime(user.id);
    if (lastCodeSent) {
      const timeSinceLastCode = Date.now() - lastCodeSent.getTime();
      const minutesSinceLastCode = Math.floor(timeSinceLastCode / 1000 / 60);
      
      if (minutesSinceLastCode < 1) {
        return NextResponse.json(
          { error: "Please wait at least 1 minute before requesting a new code" },
          { status: 429 }
        );
      }
    }

    const verificationCode = generateVerificationCode();
    const codeHash = await hashCode(verificationCode);
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 15);

    await storeVerificationCode(user.id, codeHash, expiresAt);

    try {
      await sendVerificationEmail(email, verificationCode);
      logger.info("Verification email sent successfully", { email });
      
      return NextResponse.json(
        { success: true, message: "Verification code sent to your email" },
        { status: 200 }
      );
    } catch (emailError) {
      logger.error("Failed to send verification email", { email, error: emailError });
      return NextResponse.json(
        { error: "Failed to send verification email. Please try again." },
        { status: 500 }
      );
    }
  } catch (error) {
    logger.error("Resend verification error", { error });
    return NextResponse.json(
      { error: "Failed to resend verification code" },
      { status: 500 }
    );
  }
}
