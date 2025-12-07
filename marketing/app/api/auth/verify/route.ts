import { NextResponse } from "next/server";
import { getSession, createSession } from "@/lib/auth";
import { validateCode } from "@/lib/verification";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  try {
    const session = await getSession();
    
    if (!session) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { code } = body;

    if (!code || typeof code !== "string" || code.length !== 6) {
      return NextResponse.json(
        { error: "Please enter a valid 6-digit verification code" },
        { status: 400 }
      );
    }

    const result = await validateCode(session.userId, code);

    if (!result.success) {
      return NextResponse.json(
        { error: result.error },
        { status: 400 }
      );
    }

    await createSession(session.userId, true);

    return NextResponse.json(
      { success: true, message: "Email verified successfully" },
      { status: 200 }
    );
  } catch (error) {
    logger.error("Verification error", { error });
    return NextResponse.json(
      { error: "Failed to verify code" },
      { status: 500 }
    );
  }
}
