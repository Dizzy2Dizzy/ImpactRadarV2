"""Main FastAPI application"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import time
import os
from slowapi.middleware import SlowAPIMiddleware

from api.config import settings
from api.ratelimit import limiter, plan_limit
from api.routers import auth, companies, events, watchlist, impact, portfolio, portfolio_risk, scanners, stream, pricing, billing, keys, analytics, scores, alerts, notifications, websocket, stats, demo, account, ai, backtesting, correlation, charts, peers, preferences, projector, x_feed, ml_scores, data_quality, accuracy, patterns, insider, dashboard, admin, signals, ensemble, sentiment, explainability, custom_alerts, sectors, trade_signals, history, export, digests, forum, modeling, changelog, playbooks, insights
from api.scheduler import start_scheduler, stop_scheduler
from api.utils.metrics import get_metrics_text
from api.schemas.errors import ErrorCode
from api.utils.exceptions import ReleaseRadarException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api")


def _strip_sensitive_data(event):
    """Remove PII and sensitive data before sending to Sentry"""
    if event.get("request"):
        request = event["request"]
        
        if request.get("cookies"):
            request["cookies"] = {}
        
        if request.get("headers"):
            headers = request["headers"]
            sensitive_headers = ["authorization", "cookie", "x-api-key", "api-key"]
            for header in sensitive_headers:
                if header in headers:
                    headers[header] = "REDACTED"
        
        if request.get("data"):
            data = request["data"]
            if isinstance(data, dict):
                sensitive_fields = ["password", "token", "api_key", "secret", "apiKey"]
                for field in sensitive_fields:
                    if field in data:
                        data[field] = "REDACTED"
    
    if event.get("user"):
        user = event["user"]
        if "email" in user:
            del user["email"]
        if "ip_address" in user:
            del user["ip_address"]
    
    if event.get("extra"):
        extra = event["extra"]
        sensitive_keys = ["PASSWORD", "TOKEN", "API_KEY", "SECRET", "DATABASE_URL", "SECRET_KEY"]
        for key in list(extra.keys()):
            if any(s in key.upper() for s in sensitive_keys):
                extra[key] = "REDACTED"
    
    return event


# Initialize Sentry for error monitoring
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENV", "development")),
            traces_sample_rate=0.2 if os.getenv("ENV") == "production" else 1.0,
            send_default_pii=False,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR
                ),
            ],
            before_send=lambda event, hint: _strip_sensitive_data(event),
        )
        logger.info("Sentry error monitoring initialized")
    else:
        logger.info("Sentry DSN not configured, error monitoring disabled")
except ImportError:
    logger.warning("sentry-sdk not installed, error monitoring disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting Impact Radar API...")
    
    # Auto-create database tables (handle duplicate index/table gracefully)
    from backend.database import engine
    from backend.releaseradar.db.models import Base
    from sqlalchemy.exc import ProgrammingError
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except ProgrammingError as e:
        # Handle duplicate table/index errors gracefully (schema already exists)
        if "already exists" in str(e):
            logger.info("Database tables already exist, skipping creation")
        else:
            raise
    
    # Initialize WebSocket hub
    from api.websocket.hub import get_hub
    get_hub()
    logger.info("WebSocket hub initialized")
    
    # Ensure ApiKey quota columns exist (migration for existing DBs)
    from api.db_bootstrap import ensure_apikey_quota_columns
    ensure_apikey_quota_columns()
    logger.info("API key quota columns verified")
    
    # Start background scheduler
    start_scheduler()
    logger.info("Background scanners started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Impact Radar API...")
    stop_scheduler()
    logger.info("Background scanners stopped")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description="Event-driven signal engine for equity/biotech traders. Provides programmatic access to market events, scoring, portfolio analysis, and real-time alerts.",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "events", "description": "Event data and search operations"},
        {"name": "companies", "description": "Company information and universe data"},
        {"name": "portfolio", "description": "Portfolio management and risk exposure analysis"},
        {"name": "alerts", "description": "Alert creation and management"},
        {"name": "watchlist", "description": "Watchlist management"},
        {"name": "scanners", "description": "Scanner status and manual triggers"},
        {"name": "auth", "description": "Authentication and authorization"},
        {"name": "analytics", "description": "Analytics and scoring endpoints"},
        {"name": "scores", "description": "Event scoring and impact analysis"},
        {"name": "billing", "description": "Billing and subscription management"},
        {"name": "ai", "description": "RadarQuant AI - RQ-1 Event Intelligence Engine"},
        {"name": "backtesting", "description": "Backtesting and prediction accuracy validation"},
        {"name": "correlation", "description": "Event correlation analysis and pattern discovery"},
        {"name": "charts", "description": "Price charts with event annotations for visual analysis"},
        {"name": "peers", "description": "Peer comparison - Find and compare similar events on peer companies"},
        {"name": "projector", "description": "Advanced interactive trading charts with OHLCV data, technical indicators, and event overlays"},
        {"name": "accuracy", "description": "Prediction accuracy metrics and performance tracking"},
        {"name": "custom-alerts", "description": "Custom alert rules with user-defined thresholds"},
        {"name": "sectors", "description": "Sector-level analysis, rotation signals, and performance metrics"},
        {"name": "trade-signals", "description": "Trade recommendations with entry/exit suggestions and position sizing"},
        {"name": "history", "description": "Historical pattern matching, similar events discovery, and outcome statistics"},
    ]
)

# Add SlowAPI state and middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["content-type", "x-api-key", "authorization"],
)


# Access logging middleware
@app.middleware("http")
async def access_log_middleware(request: Request, call_next):
    """Log all API requests with plan, key, and timing"""
    t0 = time.time()
    response = await call_next(request)
    ms = int((time.time() - t0) * 1000)
    
    key_prefix = getattr(request.state, "api_key_hash", "")[:8] if hasattr(request.state, "api_key_hash") else ""
    plan = getattr(request.state, "plan", "public") if hasattr(request.state, "plan") else "public"
    
    api_logger.info(
        f"{request.method} {request.url.path} {response.status_code} {ms}ms "
        f"plan={plan} key={key_prefix}"
    )
    
    return response


# Global exception handlers
@app.exception_handler(ReleaseRadarException)
async def release_radar_exception_handler(request: Request, exc: ReleaseRadarException):
    """Handle custom Impact Radar exceptions with standard format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": str(exc.detail),
            "details": exc.details,
            "status_code": exc.status_code,
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTPException with standard format"""
    # Map status codes to error codes
    error_code_map = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        402: ErrorCode.PAYMENT_REQUIRED,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_ERROR,
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": str(exc.detail),
            "details": getattr(exc, "details", None),
            "status_code": exc.status_code,
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": ErrorCode.VALIDATION_ERROR,
            "message": "Validation error",
            "details": {"errors": exc.errors()},
            "status_code": 422,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unexpected errors"""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": ErrorCode.INTERNAL_ERROR,
            "message": "An unexpected error occurred",
            "details": None,  # Don't expose internal errors
            "status_code": 500,
        }
    )


# Include routers
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(events.router)
app.include_router(watchlist.router)
app.include_router(impact.router)
app.include_router(portfolio.router)
app.include_router(portfolio_risk.router)
app.include_router(scanners.router)
app.include_router(stream.router)
app.include_router(pricing.router)
app.include_router(billing.router)
app.include_router(keys.router)
app.include_router(analytics.router)
app.include_router(scores.router)
app.include_router(alerts.router)
app.include_router(notifications.router)
app.include_router(websocket.router)
app.include_router(stats.router)
app.include_router(demo.router)
app.include_router(account.router)
app.include_router(ai.router)
app.include_router(backtesting.router)
app.include_router(correlation.router)
app.include_router(charts.router)
app.include_router(peers.router)
app.include_router(preferences.router)
app.include_router(projector.router)
app.include_router(x_feed.router)
app.include_router(ml_scores.router)
app.include_router(data_quality.router)
app.include_router(accuracy.router)
app.include_router(patterns.router)
app.include_router(insider.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(changelog.router)
app.include_router(signals.router)
app.include_router(ensemble.router)
app.include_router(sentiment.router)
app.include_router(explainability.router)
app.include_router(custom_alerts.router)
app.include_router(sectors.router)
app.include_router(trade_signals.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(digests.router)
app.include_router(forum.router)
app.include_router(modeling.router)
app.include_router(playbooks.router)
app.include_router(insights.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Impact Radar API",
        "version": settings.API_VERSION,
        "status": "running"
    }


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/debug-sentry")
async def debug_sentry():
    """
    Test endpoint for Sentry error monitoring.
    
    Throws a test error to verify Sentry integration is working.
    Check your Sentry dashboard after calling this endpoint.
    
    WARNING: Only use in development/staging environments.
    """
    logger.info("Triggering test error for Sentry verification")
    raise Exception("Test error from /debug-sentry endpoint - Sentry integration test")


@app.get("/features")
async def get_feature_flags():
    """
    Return current feature flags for frontend.
    
    Exposes feature toggles to control V1 vs Beta/Labs features:
    - enableLiveWs: Real-time WebSocket/SSE streaming
    - enableLabsUi: Beta/Labs UI features
    - enableXSentiment: X.com social sentiment analysis
    - enableAlertsBeta: Alerts system (if still flaky)
    - enableAdvancedAnalytics: Advanced analytics dashboards
    
    All flags default to false for conservative V1 launch.
    """
    from releaseradar.feature_flags import feature_flags
    return feature_flags.to_dict()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """
    Prometheus-style metrics endpoint.
    
    Exposes counters for:
    - scored_events_total: Total events scored
    - rescore_errors_total: Total rescore errors
    - rescore_requests_total: Total rescore requests
    - score_cache_hits_total: Cache hits
    - score_cache_misses_total: Cache misses
    - api_uptime_seconds: API uptime
    """
    return PlainTextResponse(content=get_metrics_text())
