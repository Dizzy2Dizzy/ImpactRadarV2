import bcrypt from "bcryptjs";
import crypto from "crypto";
import { db } from "./db";
import { passwordResetTokens, users } from "./schema";
import { eq, and, desc, isNull } from "drizzle-orm";

export function generateResetToken(): string {
  return crypto.randomBytes(32).toString('hex');
}

export async function hashToken(token: string): Promise<string> {
  return bcrypt.hash(token, 10);
}

export async function storeResetToken(
  userId: number,
  tokenHash: string,
  expiresAt: Date
): Promise<void> {
  await invalidateOldTokens(userId);
  
  await db.insert(passwordResetTokens).values({
    userId,
    tokenHash,
    expiresAt,
  });
}

export async function invalidateOldTokens(userId: number): Promise<void> {
  const now = new Date();
  await db
    .update(passwordResetTokens)
    .set({ consumedAt: now })
    .where(
      and(
        eq(passwordResetTokens.userId, userId),
        isNull(passwordResetTokens.consumedAt)
      )
    );
}

const MAX_RESET_ATTEMPTS = 5;

export async function validateResetToken(
  token: string,
  email: string
): Promise<{ success: boolean; userId?: number; error?: string }> {
  const GENERIC_ERROR = "Invalid or expired reset token. Please request a new password reset.";
  
  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.email, email))
    .limit(1);

  if (!user) {
    return { success: false, error: GENERIC_ERROR };
  }

  const allTokens = await db
    .select()
    .from(passwordResetTokens)
    .where(
      and(
        eq(passwordResetTokens.userId, user.id),
        isNull(passwordResetTokens.consumedAt)
      )
    )
    .orderBy(desc(passwordResetTokens.createdAt));

  if (allTokens.length === 0) {
    return { success: false, error: GENERIC_ERROR };
  }

  let validToken = null;
  const checkedTokens: typeof allTokens = [];
  
  for (const dbToken of allTokens) {
    if (new Date() > dbToken.expiresAt) {
      continue;
    }

    if (dbToken.attempts >= MAX_RESET_ATTEMPTS) {
      continue;
    }

    checkedTokens.push(dbToken);
    
    const isValid = await bcrypt.compare(token, dbToken.tokenHash);
    if (isValid) {
      validToken = dbToken;
      break;
    }
  }

  if (!validToken) {
    for (const checkedToken of checkedTokens) {
      await db
        .update(passwordResetTokens)
        .set({ attempts: checkedToken.attempts + 1 })
        .where(eq(passwordResetTokens.id, checkedToken.id));
    }
    
    return { success: false, error: GENERIC_ERROR };
  }

  await db
    .update(passwordResetTokens)
    .set({ consumedAt: new Date() })
    .where(eq(passwordResetTokens.id, validToken.id));

  return { success: true, userId: user.id };
}

export async function getLastResetRequestTime(email: string): Promise<Date | null> {
  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.email, email))
    .limit(1);

  if (!user) {
    return null;
  }

  const [token] = await db
    .select()
    .from(passwordResetTokens)
    .where(eq(passwordResetTokens.userId, user.id))
    .orderBy(desc(passwordResetTokens.createdAt))
    .limit(1);

  return token ? token.createdAt : null;
}
