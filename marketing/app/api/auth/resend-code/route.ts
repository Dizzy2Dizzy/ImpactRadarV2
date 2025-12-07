import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { eq } from "drizzle-orm";
import {
  generateVerificationCode,
  hashCode,
  storeVerificationCode,
  invalidateOldCodes,
  getLastCodeSentTime,
} from "@/lib/verification";
import { sendVerificationEmail } from "@/lib/email";
import { logger } from "@/lib/logger";

const RESEND_COOLDOWN_SECONDS = 60;

export async function POST(request: Request) {
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

    if (user.isVerified) {
      return NextResponse.json(
        { error: "Email is already verified" },
        { status: 400 }
      );
    }

    const lastCodeSentTime = await getLastCodeSentTime(session.userId);

    if (lastCodeSentTime) {
      const timeSinceLastCode = Math.floor(
        (new Date().getTime() - lastCodeSentTime.getTime()) / 1000
      );

      if (timeSinceLastCode < RESEND_COOLDOWN_SECONDS) {
        const remainingTime = RESEND_COOLDOWN_SECONDS - timeSinceLastCode;
        return NextResponse.json(
          {
            error: `Please wait ${remainingTime} seconds before requesting a new code`,
            remainingTime,
          },
          { status: 429 }
        );
      }
    }

    await invalidateOldCodes(session.userId);

    const verificationCode = generateVerificationCode();
    const codeHash = await hashCode(verificationCode);
    const expiresAt = new Date();
    expiresAt.setMinutes(expiresAt.getMinutes() + 15);

    await storeVerificationCode(session.userId, codeHash, expiresAt);

    try {
      await sendVerificationEmail(user.email || "", verificationCode);
    } catch (emailError) {
      logger.error("Failed to send verification email", { error: emailError });
      return NextResponse.json(
        { error: "Failed to send verification email. Please try again later." },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { success: true, message: "Verification code sent successfully" },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Resend code error", { error });
    return NextResponse.json(
      { error: "Failed to resend verification code" },
      { status: 500 }
    );
  }
}
