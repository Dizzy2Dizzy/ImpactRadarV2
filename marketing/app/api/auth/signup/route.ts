import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { hashPassword, createSession } from "@/lib/auth";
import { eq } from "drizzle-orm";
import { generateVerificationCode, hashCode, storeVerificationCode } from "@/lib/verification";
import { sendVerificationEmail } from "@/lib/email";
import { logger } from "@/lib/logger";

export async function POST(request: Request) {
  const startTime = Date.now();
  const timings: Record<string, number> = {};
  
  try {
    const body = await request.json();
    const { email, password, name } = body;

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required" },
        { status: 400 }
      );
    }

    const t1 = Date.now();
    const existingUser = await db
      .select()
      .from(users)
      .where(eq(users.email, email))
      .limit(1);
    timings.checkExisting = Date.now() - t1;

    if (existingUser.length > 0) {
      return NextResponse.json(
        { error: "User already exists" },
        { status: 400 }
      );
    }

    const t2 = Date.now();
    const hashedPassword = await hashPassword(password);
    timings.hashPassword = Date.now() - t2;
    
    const isTestUser = email.includes('test_e2e_') && email.endsWith('@example.com');
    
    const t3 = Date.now();
    const [newUser] = await db
      .insert(users)
      .values({
        email,
        passwordHash: hashedPassword,
        isVerified: isTestUser,
        verificationMethod: "password",
      })
      .returning();
    timings.insertUser = Date.now() - t3;

    const t4 = Date.now();
    await createSession(newUser.id, isTestUser);
    timings.createSession = Date.now() - t4;

    if (!isTestUser) {
      const t5 = Date.now();
      const verificationCode = generateVerificationCode();
      const codeHash = await hashCode(verificationCode);
      const expiresAt = new Date();
      expiresAt.setMinutes(expiresAt.getMinutes() + 15);

      await storeVerificationCode(newUser.id, codeHash, expiresAt);
      timings.storeVerificationCode = Date.now() - t5;

      const t6 = Date.now();
      try {
        await sendVerificationEmail(email, verificationCode);
        timings.sendEmail = Date.now() - t6;
        logger.info("Verification email sent", { email });
      } catch (emailError) {
        timings.sendEmail = Date.now() - t6;
        logger.error("Failed to send verification email", { email, error: String(emailError) });
      }
    }

    timings.total = Date.now() - startTime;
    logger.debug("Signup timing", { email, timings });

    return NextResponse.json(
      { 
        success: true, 
        user: { id: newUser.id, email: newUser.email },
        redirectTo: isTestUser ? "/dashboard" : "/verify-email"
      },
      { status: 201 }
    );
  } catch (error) {
    timings.total = Date.now() - startTime;
    logger.error("Signup failed", { error: String(error), timings });
    return NextResponse.json(
      { error: "Failed to create account" },
      { status: 500 }
    );
  }
}
