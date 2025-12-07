import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.SESSION_SECRET || "");

// Routes that require the user to be verified
const protectedRoutes = ["/dashboard", "/app", "/account"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for WebSocket upgrade requests (HMR, etc.)
  const upgrade = request.headers.get("upgrade");
  if (upgrade === "websocket") {
    return NextResponse.next();
  }

  // Check if this is a protected route
  const isProtectedRoute = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  );

  // If not a protected route, allow access
  if (!isProtectedRoute) {
    return NextResponse.next();
  }

  // Get session token
  const token = request.cookies.get("session")?.value;

  // If no token, redirect to login
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname);
    return NextResponse.redirect(loginUrl);
  }

  try {
    // Verify the JWT token
    const verified = await jwtVerify(token, secret);
    const isVerified = verified.payload.isVerified as boolean;

    // If user is not verified, redirect to verify-email page
    if (!isVerified && pathname !== "/verify-email") {
      const verifyUrl = new URL("/verify-email", request.url);
      return NextResponse.redirect(verifyUrl);
    }

    // User is verified, allow access
    return NextResponse.next();
  } catch (error) {
    console.error("Middleware auth error:", error);
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - _next/webpack-hmr (WebSocket HMR connections)
     * - favicon.ico (favicon file)
     * - public folder (images and other static assets)
     * - api routes (backend API)
     */
    "/((?!_next/static|_next/image|_next/webpack-hmr|api|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff|woff2|ttf|eot)$).*)",
  ],
};
