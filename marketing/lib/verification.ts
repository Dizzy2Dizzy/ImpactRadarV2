import bcrypt from "bcryptjs";
import { db } from "./db";
import { verificationTokens, users } from "./schema";
import { eq, and, desc, isNull } from "drizzle-orm";

export function generateVerificationCode(): string {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

export async function hashCode(code: string): Promise<string> {
  return bcrypt.hash(code, 10);
}

export async function storeVerificationCode(
  userId: number,
  codeHash: string,
  expiresAt: Date
): Promise<void> {
  await db.insert(verificationTokens).values({
    userId,
    codeHash,
    expiresAt,
    attempts: 0,
  });
}

export async function invalidateOldCodes(userId: number): Promise<void> {
  const now = new Date();
  await db
    .update(verificationTokens)
    .set({ consumedAt: now })
    .where(
      and(
        eq(verificationTokens.userId, userId),
        isNull(verificationTokens.consumedAt)
      )
    );
}

export async function validateCode(
  userId: number,
  code: string
): Promise<{ success: boolean; error?: string }> {
  const [token] = await db
    .select()
    .from(verificationTokens)
    .where(
      and(
        eq(verificationTokens.userId, userId),
        isNull(verificationTokens.consumedAt)
      )
    )
    .orderBy(desc(verificationTokens.createdAt))
    .limit(1);

  if (!token) {
    return { success: false, error: "No verification code found. Please request a new code." };
  }

  if (new Date() > token.expiresAt) {
    return { success: false, error: "Verification code has expired. Please request a new code." };
  }

  if (token.attempts >= 5) {
    return { success: false, error: "Too many failed attempts. Please request a new code." };
  }

  const isValid = await bcrypt.compare(code, token.codeHash);

  if (!isValid) {
    await db
      .update(verificationTokens)
      .set({ attempts: token.attempts + 1 })
      .where(eq(verificationTokens.id, token.id));

    const attemptsLeft = 5 - (token.attempts + 1);
    return { 
      success: false, 
      error: `Invalid verification code. ${attemptsLeft} attempt${attemptsLeft !== 1 ? 's' : ''} remaining.` 
    };
  }

  await db
    .update(verificationTokens)
    .set({ consumedAt: new Date() })
    .where(eq(verificationTokens.id, token.id));

  await db
    .update(users)
    .set({ isVerified: true })
    .where(eq(users.id, userId));

  return { success: true };
}

export async function getLastCodeSentTime(userId: number): Promise<Date | null> {
  const [token] = await db
    .select()
    .from(verificationTokens)
    .where(eq(verificationTokens.userId, userId))
    .orderBy(desc(verificationTokens.createdAt))
    .limit(1);

  return token ? token.createdAt : null;
}
