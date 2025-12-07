import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import bcrypt from "bcryptjs";
import { db } from "./db";
import { sessions, users } from "./schema";
import { eq } from "drizzle-orm";
import crypto from "crypto";

if (!process.env.SESSION_SECRET) {
  throw new Error("SESSION_SECRET must be set in environment variables");
}

const secret = new TextEncoder().encode(process.env.SESSION_SECRET);

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function verifyPassword(
  password: string,
  hashedPassword: string
): Promise<boolean> {
  return bcrypt.compare(password, hashedPassword);
}

export async function createSession(userId: number, isVerified: boolean): Promise<string> {
  const token = await new SignJWT({ userId, isVerified })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("24h")
    .sign(secret);

  const expiresAt = new Date();
  expiresAt.setHours(expiresAt.getHours() + 24);

  await db.insert(sessions).values({
    userId,
    token: crypto.createHash("sha256").update(token).digest("hex"),
    expiresAt,
  });

  (await cookies()).set("session", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24, // 24 hours
  });

  return token;
}

export async function getSession(): Promise<{ userId: number; isVerified: boolean } | null> {
  const token = (await cookies()).get("session")?.value;
  if (!token) return null;

  try {
    const verified = await jwtVerify(token, secret);
    
    const tokenHash = crypto.createHash("sha256").update(token).digest("hex");
    const [session] = await db
      .select()
      .from(sessions)
      .where(eq(sessions.token, tokenHash))
      .limit(1);

    if (!session || session.expiresAt < new Date()) {
      if (session) {
        await db.delete(sessions).where(eq(sessions.id, session.id));
      }
      await deleteSession();
      return null;
    }

    return verified.payload as { userId: number; isVerified: boolean };
  } catch {
    return null;
  }
}

export async function deleteSession(): Promise<void> {
  const token = (await cookies()).get("session")?.value;
  
  if (token) {
    const tokenHash = crypto.createHash("sha256").update(token).digest("hex");
    await db.delete(sessions).where(eq(sessions.token, tokenHash));
  }
  
  (await cookies()).delete("session");
}

export type VerifiedUser = {
  id: number;
  email: string;
  plan: string;
  isVerified: boolean;
};

export type AuthError = {
  error: string;
  code: string;
  statusCode: number;
};

export async function requireVerifiedUser(): Promise<{ user: VerifiedUser } | { error: AuthError }> {
  const session = await getSession();
  
  if (!session) {
    return {
      error: {
        error: "Authentication required",
        code: "AUTHENTICATION_REQUIRED",
        statusCode: 401,
      },
    };
  }

  const [user] = await db
    .select()
    .from(users)
    .where(eq(users.id, session.userId))
    .limit(1);

  if (!user) {
    return {
      error: {
        error: "User not found",
        code: "USER_NOT_FOUND",
        statusCode: 401,
      },
    };
  }

  if (!user.isVerified) {
    return {
      error: {
        error: "Email verification required. Please verify your email at /verify-email",
        code: "VERIFICATION_REQUIRED",
        statusCode: 403,
      },
    };
  }

  return {
    user: {
      id: user.id,
      email: user.email || "",
      plan: user.plan || "free",
      isVerified: user.isVerified || false,
    },
  };
}
