"""
Configuration management for Impact Radar using Pydantic Settings.

Loads configuration from environment variables with type validation and sane defaults.
"""

from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key for session management")
    session_secret: str = Field(default="dev-session-secret-change-in-production", description="Session secret for cookies")
    allowed_origins: str = Field(default="http://localhost:5000", description="CORS allowed origins (comma-separated)")
    
    # Database
    database_url: str = Field(description="PostgreSQL connection URL")
    pghost: str = Field(default="localhost")
    pgport: int = Field(default=5432)
    pguser: str = Field(default="postgres")
    pgpassword: str = Field(default="")
    pgdatabase: str = Field(default="releaseradar")
    
    # Feature Flags
    enable_stripe: bool = Field(default=False, description="Enable Stripe payments")
    enable_sms_verification: bool = Field(default=False, description="Enable SMS verification")
    enable_email_verification: bool = Field(default=True, description="Enable email verification")
    enable_2fa: bool = Field(default=False, description="Enable 2FA authentication")
    enable_crypto_payments: bool = Field(default=False, description="Enable crypto payments (DISABLED)")
    
    # SEC EDGAR
    sec_edgar_user_agent: str = Field(default="Impact Radar bot@impactradar.com", description="User agent for SEC requests")
    sec_edgar_rate_limit_requests: int = Field(default=10, description="SEC API requests per period")
    sec_edgar_rate_limit_period: int = Field(default=1, description="SEC API rate limit period (seconds)")
    
    # FDA
    fda_base_url: str = Field(default="https://www.fda.gov", description="FDA base URL")
    fda_rate_limit_requests: int = Field(default=5, description="FDA requests per period")
    fda_rate_limit_period: int = Field(default=1, description="FDA rate limit period (seconds)")
    
    # YFinance
    yfinance_cache_ttl: int = Field(default=30, description="YFinance cache TTL in seconds")
    
    # Email (SMTP)
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(default="noreply@impactradar.com", description="From email address")
    smtp_from_name: str = Field(default="Impact Radar", description="From name")
    
    # SMS (Twilio)
    twilio_account_sid: str = Field(default="", description="Twilio account SID")
    twilio_auth_token: str = Field(default="", description="Twilio auth token")
    twilio_phone_number: str = Field(default="", description="Twilio phone number")
    
    # Payments (Stripe)
    stripe_api_key: str = Field(default="", description="Stripe API key (test mode)")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook secret")
    stripe_price_id_free: str = Field(default="price_free", description="Stripe price ID for free tier")
    stripe_price_id_pro: str = Field(default="price_pro", description="Stripe price ID for pro tier")
    stripe_price_id_team: str = Field(default="price_team", description="Stripe price ID for team tier")
    
    # Caching
    cache_dir: str = Field(default=".cache", description="Cache directory")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    http_cache_ttl: int = Field(default=300, description="HTTP cache TTL in seconds")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_default_requests: int = Field(default=100, description="Default rate limit requests")
    rate_limit_default_period: int = Field(default=60, description="Default rate limit period (seconds)")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    log_format: str = Field(default="json", description="Log format: json or text")
    log_file: str = Field(default="logs/releaseradar.log", description="Log file path")
    
    # Scheduler
    scheduler_enabled: bool = Field(default=True, description="Enable background scheduler")
    scanner_priority_interval_minutes: int = Field(default=5, description="Priority scanner interval")
    scanner_general_interval_minutes: int = Field(default=30, description="General scanner interval")
    housekeeping_interval_hours: int = Field(default=24, description="Housekeeping job interval")
    
    # Security
    password_min_length: int = Field(default=8, description="Minimum password length")
    password_require_uppercase: bool = Field(default=True, description="Require uppercase in password")
    password_require_lowercase: bool = Field(default=True, description="Require lowercase in password")
    password_require_numbers: bool = Field(default=True, description="Require numbers in password")
    password_require_special: bool = Field(default=True, description="Require special chars in password")
    
    verification_code_length: int = Field(default=6, description="Verification code length")
    verification_code_expiry_minutes: int = Field(default=15, description="Verification code expiry")
    verification_max_attempts: int = Field(default=5, description="Max verification attempts")
    
    session_expiry_hours: int = Field(default=24, description="Session expiry in hours")
    
    @field_validator("allowed_origins")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> List[str]:
        """Parse comma-separated allowed origins into a list."""
        return [origin.strip() for origin in v.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


# Global settings instance
settings = Settings()
