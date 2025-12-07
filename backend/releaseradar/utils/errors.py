"""
Custom exceptions for Impact Radar.

Provides domain-specific exceptions with clear error messages and
support for structured error handling.
"""

from typing import Optional, Dict, Any


class ReleaseRadarError(Exception):
    """Base exception for all Impact Radar errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
# Database Errors
# ============================================================================

class DatabaseError(ReleaseRadarError):
    """Database operation failed."""
    pass


class RecordNotFoundError(DatabaseError):
    """Database record not found."""
    pass


class DuplicateRecordError(DatabaseError):
    """Attempted to create a duplicate record."""
    pass


# ============================================================================
# Authentication & Authorization Errors
# ============================================================================

class AuthenticationError(ReleaseRadarError):
    """Authentication failed."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""
    pass


class AccountNotVerifiedError(AuthenticationError):
    """Account not verified (email or phone)."""
    pass


class SessionExpiredError(AuthenticationError):
    """User session has expired."""
    pass


class AuthorizationError(ReleaseRadarError):
    """User not authorized to perform this action."""
    pass


# ============================================================================
# Validation Errors
# ============================================================================

class ValidationError(ReleaseRadarError):
    """Data validation failed."""
    pass


class PasswordValidationError(ValidationError):
    """Password does not meet requirements."""
    pass


class EmailValidationError(ValidationError):
    """Invalid email address."""
    pass


class VerificationCodeError(ValidationError):
    """Invalid or expired verification code."""
    pass


# ============================================================================
# External Service Errors
# ============================================================================

class ExternalServiceError(ReleaseRadarError):
    """External service integration failed."""
    pass


class SECEdgarError(ExternalServiceError):
    """SEC EDGAR API error."""
    pass


class FDAError(ExternalServiceError):
    """FDA API error."""
    pass


class EmailServiceError(ExternalServiceError):
    """Email service error."""
    pass


class SMSServiceError(ExternalServiceError):
    """SMS service error."""
    pass


class StripeError(ExternalServiceError):
    """Stripe payment error."""
    pass


class YFinanceError(ExternalServiceError):
    """YFinance data retrieval error."""
    pass


# ============================================================================
# Rate Limiting Errors
# ============================================================================

class RateLimitError(ReleaseRadarError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


# ============================================================================
# Scraping Errors
# ============================================================================

class ScrapingError(ReleaseRadarError):
    """Web scraping failed."""
    pass


class ParseError(ScrapingError):
    """Failed to parse HTML/content."""
    pass


class RobotsExclusionError(ScrapingError):
    """robots.txt prohibits accessing this resource."""
    pass


# ============================================================================
# Business Logic Errors
# ============================================================================

class InvalidEventTypeError(ValidationError):
    """Invalid event type provided."""
    pass


class DuplicateEventError(ReleaseRadarError):
    """Event already exists (hash collision)."""
    pass


class ScoringError(ReleaseRadarError):
    """Failed to score event."""
    pass


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(ReleaseRadarError):
    """Application configuration error."""
    pass


class MissingSecretError(ConfigurationError):
    """Required secret/environment variable not configured."""
    pass
