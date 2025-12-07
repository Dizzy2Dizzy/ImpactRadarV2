import { NextResponse } from "next/server";
import { db } from "@/lib/db";
import { users } from "@/lib/schema";
import { createSession } from "@/lib/auth";
import { eq } from "drizzle-orm";
import { logger } from "@/lib/logger";

const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = process.env.NEXT_PUBLIC_BASE_URL 
  ? `${process.env.NEXT_PUBLIC_BASE_URL}/api/auth/google/callback`
  : "http://localhost:5000/api/auth/google/callback";

interface GoogleTokenResponse {
  access_token: string;
  id_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
}

interface GoogleUserInfo {
  id: string;
  email: string;
  verified_email: boolean;
  name?: string;
  picture?: string;
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const code = url.searchParams.get("code");
    const state = url.searchParams.get("state");
    const error = url.searchParams.get("error");

    if (error) {
      logger.error("Google OAuth error", { error });
      return NextResponse.redirect(new URL("/login?error=google_auth_failed", request.url));
    }

    if (!code) {
      return NextResponse.redirect(new URL("/login?error=no_code", request.url));
    }

    if (!GOOGLE_CLIENT_ID || !GOOGLE_CLIENT_SECRET) {
      logger.error("Google OAuth not configured");
      return NextResponse.redirect(new URL("/login?error=oauth_not_configured", request.url));
    }

    let mode = "login";
    if (state) {
      try {
        const decoded = JSON.parse(Buffer.from(state, "base64").toString());
        mode = decoded.mode || "login";
      } catch (e) {
        logger.warn("Failed to decode state", { error: String(e) });
      }
    }

    const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        code,
        client_id: GOOGLE_CLIENT_ID,
        client_secret: GOOGLE_CLIENT_SECRET,
        redirect_uri: REDIRECT_URI,
        grant_type: "authorization_code",
      }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.text();
      logger.error("Failed to exchange code for token", { error: errorData });
      return NextResponse.redirect(new URL("/login?error=token_exchange_failed", request.url));
    }

    const tokens: GoogleTokenResponse = await tokenResponse.json();

    const userInfoResponse = await fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    if (!userInfoResponse.ok) {
      logger.error("Failed to get user info");
      return NextResponse.redirect(new URL("/login?error=user_info_failed", request.url));
    }

    const googleUser: GoogleUserInfo = await userInfoResponse.json();

    if (!googleUser.email) {
      return NextResponse.redirect(new URL("/login?error=no_email", request.url));
    }

    if (!googleUser.verified_email) {
      logger.warn("Google email not verified", { email: googleUser.email });
      return NextResponse.redirect(new URL("/login?error=email_not_verified", request.url));
    }

    let [existingUser] = await db
      .select()
      .from(users)
      .where(eq(users.googleId, googleUser.id))
      .limit(1);

    if (!existingUser) {
      [existingUser] = await db
        .select()
        .from(users)
        .where(eq(users.email, googleUser.email))
        .limit(1);

      if (existingUser) {
        if (existingUser.passwordHash) {
          const shouldVerify = existingUser.isVerified || googleUser.verified_email;
          await db
            .update(users)
            .set({ 
              googleId: googleUser.id,
              isVerified: shouldVerify,
            })
            .where(eq(users.id, existingUser.id));
          
          existingUser.googleId = googleUser.id;
          existingUser.isVerified = shouldVerify;
        } else if (!existingUser.googleId) {
          await db
            .update(users)
            .set({ 
              googleId: googleUser.id,
              authProvider: "google",
              isVerified: true,
            })
            .where(eq(users.id, existingUser.id));
          
          existingUser.googleId = googleUser.id;
          existingUser.authProvider = "google";
          existingUser.isVerified = true;
        }
      }
    }

    if (existingUser) {
      const isVerified = existingUser.isVerified === true;
      await createSession(existingUser.id, isVerified);
      
      await db
        .update(users)
        .set({ lastLogin: new Date() })
        .where(eq(users.id, existingUser.id));

      logger.info("Google login successful", { userId: existingUser.id, email: googleUser.email });
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }

    const [newUser] = await db
      .insert(users)
      .values({
        email: googleUser.email,
        googleId: googleUser.id,
        authProvider: "google",
        isVerified: true,
        verificationMethod: "google",
      })
      .returning();

    await createSession(newUser.id, true);

    logger.info("Google signup successful", { userId: newUser.id, email: googleUser.email });
    return NextResponse.redirect(new URL("/dashboard", request.url));

  } catch (error) {
    logger.error("Google OAuth callback error", { error: String(error) });
    return NextResponse.redirect(new URL("/login?error=callback_failed", request.url));
  }
}
