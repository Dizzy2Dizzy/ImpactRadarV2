"""Error response schemas and error codes"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ErrorResponse(BaseModel):
    """Standard error response format"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    status_code: int


class ErrorCode:
    """Standard error codes for the application"""
    
    # Authentication
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    
    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Quota & Rate Limiting
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Plan & Payment
    UPGRADE_REQUIRED = "UPGRADE_REQUIRED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
