import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { logger } from "@/lib/logger";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const ref = searchParams.get("ref");

    if (!ref) {
      return NextResponse.json({ error: "Missing ref parameter" }, { status: 400 });
    }

    // Validate affiliate code format
    if (!/^[a-zA-Z0-9_-]{4,20}$/.test(ref)) {
      return NextResponse.json({ error: "Invalid ref code" }, { status: 400 });
    }

    // Set cookie to track referral (90-day expiration)
    const cookieStore = cookies();
    const expirationDate = new Date();
    expirationDate.setDate(expirationDate.getDate() + 90);

    cookieStore.set("affiliate_ref", ref, {
      expires: expirationDate,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
    });

    logger.info("Affiliate referral tracked", {
      code: ref,
      userAgent: request.headers.get("user-agent"),
      referer: request.headers.get("referer"),
    });

    // In production, you would:
    // 1. Verify affiliate code exists in database
    // 2. Increment click counter
    // 3. Store detailed analytics (IP, user agent, referrer, etc.)

    // SECURITY: Validate redirect URL to prevent open redirect attacks
    // Protects against: //evil.com, \\evil.com, https:evil.com, /\evil.com, etc.
    const redirectParam = searchParams.get("redirect") || "/";
    let redirectUrl = "/";

    try {
      // Reject any URL with backslashes (Windows path tricks like \\evil.com)
      if (redirectParam.includes("\\")) {
        logger.warn("Blocked redirect with backslash", { redirectParam });
        redirectUrl = "/";
      }
      // Check if it's a safe relative path (must start with / but not //)
      else if (redirectParam.startsWith("/") && !redirectParam.startsWith("//")) {
        // Additional validation: check decoded URL for bypass attempts
        try {
          const decoded = decodeURIComponent(redirectParam);
          if (decoded.includes("\\") || decoded.match(/^\/\//)) {
            logger.warn("Blocked encoded redirect bypass", { redirectParam });
            redirectUrl = "/";
          } else {
            redirectUrl = redirectParam;
          }
        } catch {
          // Invalid encoding, use original if it passes basic checks
          redirectUrl = redirectParam;
        }
      }
      // For absolute URLs or protocol-relative URLs, parse and validate strictly
      else {
        const parsedUrl = new URL(redirectParam, request.url);
        
        // Whitelist of allowed domains
        const allowedHosts = ["impactradar.co", "www.impactradar.co"];
        
        // Validate protocol is HTTP or HTTPS only (reject javascript:, data:, etc.)
        if (parsedUrl.protocol !== "http:" && parsedUrl.protocol !== "https:") {
          logger.warn("Blocked non-HTTP(S) protocol", { protocol: parsedUrl.protocol });
          redirectUrl = "/";
        }
        // Validate hostname is in whitelist
        else if (!allowedHosts.includes(parsedUrl.hostname)) {
          logger.warn("Blocked redirect to untrusted domain", { hostname: parsedUrl.hostname });
          redirectUrl = "/";
        }
        // Extract only path, search, and hash (relative to our domain)
        else {
          redirectUrl = parsedUrl.pathname + parsedUrl.search + parsedUrl.hash;
        }
      }
    } catch (error) {
      // If URL parsing fails, default to homepage
      logger.warn("Invalid redirect URL, using default", { redirectParam, error });
      redirectUrl = "/";
    }

    return NextResponse.redirect(new URL(redirectUrl, request.url));
  } catch (error) {
    logger.error("Affiliate tracking error", { error });
    return NextResponse.json(
      { error: "Failed to track referral" },
      { status: 500 }
    );
  }
}
