/**
 * API client with standardized error handling
 */

import { showToast } from './toast';

export interface ApiError {
  error_code: string;
  message: string;
  details?: any;
  status_code: number;
}

export class ApiErrorResponse extends Error {
  constructor(
    public error_code: string,
    public message: string,
    public status_code: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiErrorResponse';
  }
}

export async function apiRequest<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      cache: 'no-store',
      headers: {
        ...options?.headers,
        'Cache-Control': 'no-cache',
      },
    });
    
    if (!response.ok) {
      let error: ApiError;
      
      try {
        error = await response.json();
      } catch {
        error = {
          error_code: 'UNKNOWN_ERROR',
          message: 'An unexpected error occurred',
          status_code: response.status
        };
      }
      
      handleApiError(error);
      
      throw new ApiErrorResponse(
        error.error_code,
        error.message,
        error.status_code,
        error.details
      );
    }
    
    return response.json();
  } catch (e) {
    if (e instanceof ApiErrorResponse) {
      throw e;
    }
    
    showToast('Network error. Please check your connection.', 'error');
    throw e;
  }
}

function handleApiError(error: ApiError) {
  switch (error.error_code) {
    case 'QUOTA_EXCEEDED':
      showToast('API quota exceeded. Please upgrade your plan.', 'error');
      break;
      
    case 'UPGRADE_REQUIRED':
      showToast(error.message, 'warning');
      break;
      
    case 'RATE_LIMIT_EXCEEDED':
      showToast('Too many requests. Please wait a moment.', 'error');
      break;
      
    case 'UNAUTHORIZED':
      showToast('Please log in to continue.', 'error');
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500);
      break;
      
    case 'FORBIDDEN':
      showToast('You do not have permission to perform this action.', 'error');
      break;
      
    case 'NOT_FOUND':
      showToast(error.message || 'Resource not found', 'error');
      break;
      
    case 'VALIDATION_ERROR':
      // Don't show toast for validation errors - let components handle these
      break;
      
    case 'INVALID_INPUT':
      showToast(error.message || 'Invalid input provided', 'error');
      break;
      
    default:
      showToast(error.message || 'An error occurred', 'error');
  }
}
