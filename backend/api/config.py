"""Configuration for FastAPI application"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Settings
    API_TITLE: str = "Impact Radar API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    
    # Database
    DATABASE_URL: str
    
    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5000",
        "http://0.0.0.0:5000",
        "https://78e4845b-fe38-4301-80db-29f02c5bd8b5-00-16mm1lvsjyta9.kirk.replit.dev"
    ]
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    
    # Email & SMS
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    TWILIO_SID: str = ""
    TWILIO_TOKEN: str = ""
    TWILIO_FROM: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars (like ENABLE_LIVE_WS)


settings = Settings()
