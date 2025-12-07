/**
 * X.com Feed API Route
 * Proxies requests to the FastAPI backend for X.com sentiment analysis
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

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    
    // Check if user is authenticated and verified
    const authResult = await requireVerifiedUser();
    
    // If there's an error (not authenticated or not verified)
    if ('error' in authResult) {
      return NextResponse.json(
        { 
          error: authResult.error.error,
          code: authResult.error.code
        },
        { status: authResult.error.statusCode }
      );
    }
    
    // User is verified, create FastAPI JWT token
    const { user } = authResult;
    const token = await new SignJWT({
      sub: user.email,
      user_id: user.id,
      plan: user.plan,
    })
      .setProtectedHeader({ alg: 'HS256' })
      .setExpirationTime('24h')
      .sign(jwtSecret);
    
    // Build backend URL with query parameters
    const backendParams = new URLSearchParams();
    
    const tickers = searchParams.get('tickers');
    const days = searchParams.get('days');
    const sentimentFilter = searchParams.get('sentiment_filter');
    
    if (tickers) backendParams.set('tickers', tickers);
    if (days) backendParams.set('days', days);
    if (sentimentFilter) backendParams.set('sentiment_filter', sentimentFilter);
    
    const url = `${BACKEND_URL}/api/x-feed${backendParams.toString() ? `?${backendParams.toString()}` : ''}`;
    
    // Make the proxied request with timeout
    const controller = new AbortController();
    const timeout = 30000; // 30 seconds
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      const responseBody = await response.text();
      
      // Handle different error responses
      if (!response.ok) {
        let errorData;
        try {
          errorData = JSON.parse(responseBody);
        } catch {
          errorData = { detail: 'Backend request failed' };
        }
        
        // Map backend errors to appropriate status codes
        if (response.status === 401) {
          return NextResponse.json(
            { error: 'Unauthorized', detail: errorData.detail || 'Invalid or missing token' },
            { status: 401 }
          );
        } else if (response.status === 429) {
          return NextResponse.json(
            { error: 'Rate limit exceeded', detail: errorData.detail || 'Too many requests' },
            { status: 429 }
          );
        } else if (response.status === 422) {
          return NextResponse.json(
            { error: 'Invalid parameters', detail: errorData.detail || 'Invalid request parameters' },
            { status: 422 }
          );
        } else {
          return NextResponse.json(
            { error: 'Backend error', detail: errorData.detail || 'An error occurred' },
            { status: response.status }
          );
        }
      }
      
      // Return successful response
      return new NextResponse(responseBody, {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
    } catch (fetchError: any) {
      clearTimeout(timeoutId);
      
      // Handle timeout
      if (fetchError.name === 'AbortError') {
        return NextResponse.json(
          { error: 'Request timed out', detail: 'The request took too long. Please try again.' },
          { status: 504 }
        );
      }
      
      // Re-throw other errors
      throw fetchError;
    }
    
  } catch (error) {
    logger.error('X feed proxy error', { error });
    return NextResponse.json(
      { error: 'Internal server error', detail: 'Failed to process request' },
      { status: 500 }
    );
  }
}
