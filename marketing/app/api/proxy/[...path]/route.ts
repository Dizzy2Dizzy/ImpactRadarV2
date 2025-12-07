/**
 * API Proxy Route
 * Forwards all API requests to the FastAPI backend
 * Transparently injects FastAPI JWT tokens from Next.js session
 */

import { NextRequest, NextResponse } from 'next/server';
import { requireVerifiedUser } from '@/lib/auth';
import { SignJWT } from 'jose';
import { logger } from '@/lib/logger';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

if (!process.env.JWT_SECRET) {
  throw new Error('JWT_SECRET must be set in environment variables');
}

const jwtSecret = new TextEncoder().encode(process.env.JWT_SECRET);

const PREMIUM_ENDPOINTS = [
  '/analytics',
  '/projector',
  '/correlation',
  '/backtesting',
  '/ai',
  '/x-feed',
  '/portfolio/insights',
  '/peer-analysis',
  '/alerts',
  '/scanners/run',
  '/charts',
  '/peers',
  '/preferences',
  '/stream',
  '/websocket',
  '/ws',
];

const PUBLIC_ENDPOINTS = [
  '/analytics/market-regime',
  '/events/public',
];

// Endpoints that can be cached on the client for short periods
const CACHEABLE_ENDPOINTS: { [key: string]: number } = {
  '/dashboard/init': 30,
  '/dashboard/stats': 60,
  '/features': 300,
  '/scanners/count': 60,
  '/scanners/status': 30,
  '/companies/universe': 60,
};

function getCacheDuration(path: string): number | null {
  for (const [endpoint, duration] of Object.entries(CACHEABLE_ENDPOINTS)) {
    if (path.startsWith(endpoint)) {
      return duration;
    }
  }
  return null;
}

function isPremiumEndpoint(path: string): boolean {
  return PREMIUM_ENDPOINTS.some(premium => path.startsWith(premium));
}

function isPublicEndpoint(path: string): boolean {
  return PUBLIC_ENDPOINTS.some(pub => path.startsWith(pub));
}

function requiresPremiumPlan(plan: string): boolean {
  return plan === 'pro' || plan === 'team';
}

function isAdminEndpoint(path: string): boolean {
  return path.startsWith('/admin');
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params.path, 'GET');
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params.path, 'POST');
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params.path, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params.path, 'DELETE');
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const params = await context.params;
  return proxyRequest(request, params.path, 'PATCH');
}

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
) {
  try {
    const path = '/' + pathSegments.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const url = `${BACKEND_URL}${path}${searchParams ? `?${searchParams}` : ''}`;

    // Get content type early to determine how to handle the request
    const contentType = request.headers.get('content-type') || '';
    const isMultipart = contentType.includes('multipart/form-data');
    
    // Forward headers
    const headers: HeadersInit = {};
    request.headers.forEach((value, key) => {
      const lowerKey = key.toLowerCase();
      // Skip host, authorization headers
      // For multipart/form-data, also skip content-type and content-length (fetch will set them correctly)
      if (lowerKey !== 'host' && lowerKey !== 'authorization' && 
          !(isMultipart && (lowerKey === 'content-type' || lowerKey === 'content-length'))) {
        headers[key] = value;
      }
    });

    // Admin endpoints bypass normal auth and use X-Admin-Key instead
    // Public endpoints also bypass auth
    if (!isAdminEndpoint(path) && !isPublicEndpoint(path)) {
      // Check if user is authenticated and verified
      const authResult = await requireVerifiedUser();
      
      // If there's an error (not authenticated or not verified)
      if ('error' in authResult) {
        // Return error response with proper status code
        return NextResponse.json(
          { 
            error: authResult.error.error,
            code: authResult.error.code
          },
          { status: authResult.error.statusCode }
        );
      }
      
      // User is verified, inject FastAPI JWT token
      const { user } = authResult;
      
      // Check if endpoint requires premium plan
      if (isPremiumEndpoint(path) && !requiresPremiumPlan(user.plan)) {
        return NextResponse.json(
          { 
            error: 'You do not have access, please upgrade for access.',
            code: 'PREMIUM_FEATURE_REQUIRED',
            plan_required: 'pro'
          },
          { status: 403 }
        );
      }
      
      const token = await new SignJWT({
        sub: user.email,
        user_id: user.id,
        plan: user.plan,
      })
        .setProtectedHeader({ alg: 'HS256' })
        .setExpirationTime('24h')
        .sign(jwtSecret);
      
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Get request body for non-GET requests
    let body: BodyInit | undefined;
    if (method !== 'GET' && method !== 'DELETE') {
      try {
        if (isMultipart) {
          body = await request.formData();
        } else {
          body = await request.text();
        }
      } catch (error) {
        // No body or already consumed
      }
    }

    // Make the proxied request with timeout
    const controller = new AbortController();
    const timeout = 30000; // 30 seconds timeout
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        method,
        headers,
        body,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

      // Get response body
      const responseBody = await response.text();

      // Build response headers
      const responseHeaders: HeadersInit = {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      };
      
      // Add cache headers for cacheable GET endpoints
      if (method === 'GET' && response.ok) {
        const cacheDuration = getCacheDuration(path);
        if (cacheDuration) {
          responseHeaders['Cache-Control'] = `private, max-age=${cacheDuration}, stale-while-revalidate=${cacheDuration * 2}`;
        }
      }

      // Return the response
      return new NextResponse(responseBody, {
        status: response.status,
        headers: responseHeaders,
      });
    } catch (fetchError: any) {
      clearTimeout(timeoutId);
      
      // If the request was aborted due to timeout
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { detail: 'Request timed out. Please try again.' },
          { status: 504 }  // Gateway Timeout
        );
      }
      
      // Re-throw other errors
      throw fetchError;
    }
  } catch (error) {
    logger.error('Proxy error', { error });
    return NextResponse.json(
      { detail: 'Proxy request failed' },
      { status: 500 }
    );
  }
}
