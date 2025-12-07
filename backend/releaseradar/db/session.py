"""
Database session management with SQLAlchemy 2.0.

Provides engine configuration, session creation, context managers
for safe database access with proper connection pooling, health checks,
and automatic transaction rollback.
"""

import time
import threading
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.pool import Pool
from loguru import logger

from releaseradar.config import settings
from releaseradar.utils.errors import DatabaseError


# ============================================================================
# Connection Pool Configuration with Enhanced Health Checks
# ============================================================================

# Create engine with connection pooling and timeout settings
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Number of connections to maintain
    max_overflow=20,  # Maximum overflow connections
    pool_timeout=30,  # Timeout waiting for connection from pool
    pool_recycle=1800,  # Recycle connections after 30 minutes
    echo=settings.debug,  # Log SQL queries in debug mode
    connect_args={
        "connect_timeout": 10,  # Connection timeout in seconds
        "options": "-c statement_timeout=60000",  # 60 second query timeout
    },
)

# Create session factory
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,  # Prevent lazy load issues after commit
    )
)


# ============================================================================
# Connection Pool Health Monitoring
# ============================================================================

class ConnectionPoolHealth:
    """Monitor and manage database connection pool health."""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._stats: Dict[str, Any] = {
            "total_checkouts": 0,
            "total_checkins": 0,
            "failed_checkouts": 0,
            "last_health_check": None,
            "is_healthy": True,
            "unhealthy_since": None,
            "recovery_attempts": 0,
        }
        self._error_window: list = []  # Track errors within time window
        self._error_window_seconds = 60  # 1 minute window
        self._error_threshold = 5  # Errors before marking unhealthy
    
    def record_checkout(self):
        """Record a successful connection checkout."""
        with self._lock:
            self._stats["total_checkouts"] += 1
    
    def record_checkin(self):
        """Record a connection checkin."""
        with self._lock:
            self._stats["total_checkins"] += 1
    
    def record_error(self, error_type: str = "unknown"):
        """Record a connection error and check health status."""
        now = datetime.utcnow()
        with self._lock:
            self._stats["failed_checkouts"] += 1
            
            # Add to error window
            self._error_window.append(now)
            
            # Clean old errors from window
            cutoff = now - timedelta(seconds=self._error_window_seconds)
            self._error_window = [t for t in self._error_window if t > cutoff]
            
            # Check if we exceeded threshold
            if len(self._error_window) >= self._error_threshold:
                if self._stats["is_healthy"]:
                    logger.warning(
                        f"Connection pool marked UNHEALTHY: {len(self._error_window)} errors "
                        f"in {self._error_window_seconds}s"
                    )
                self._stats["is_healthy"] = False
                self._stats["unhealthy_since"] = now
    
    def mark_healthy(self):
        """Mark the connection pool as healthy after successful recovery."""
        with self._lock:
            if not self._stats["is_healthy"]:
                logger.info("Connection pool marked HEALTHY after recovery")
            self._stats["is_healthy"] = True
            self._stats["unhealthy_since"] = None
            self._stats["recovery_attempts"] = 0
            self._error_window = []
    
    def is_healthy(self) -> bool:
        """Check if the connection pool is healthy."""
        with self._lock:
            return self._stats["is_healthy"]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            pool = engine.pool
            return {
                **self._stats,
                "pool_size": pool.size() if hasattr(pool, 'size') else None,
                "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
                "checked_out": pool.checkedout() if hasattr(pool, 'checkedout') else None,
                "overflow": pool.overflow() if hasattr(pool, 'overflow') else None,
                "recent_errors": len(self._error_window),
            }
    
    def attempt_recovery(self) -> bool:
        """Attempt to recover the connection pool."""
        with self._lock:
            self._stats["recovery_attempts"] += 1
        
        try:
            # Dispose all current connections and create fresh ones
            engine.dispose()
            logger.info("Connection pool disposed for recovery")
            
            # Test with a simple query
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.mark_healthy()
            return True
            
        except Exception as e:
            logger.error(f"Connection pool recovery failed: {e}")
            return False


# Global health monitor instance
pool_health = ConnectionPoolHealth()


# Register SQLAlchemy pool events for monitoring
@event.listens_for(Pool, "checkout")
def on_checkout(dbapi_conn, connection_record, connection_proxy):
    """Called when a connection is checked out from the pool."""
    pool_health.record_checkout()


@event.listens_for(Pool, "checkin")
def on_checkin(dbapi_conn, connection_record):
    """Called when a connection is checked back into the pool."""
    pool_health.record_checkin()


@event.listens_for(Pool, "invalidate")
def on_invalidate(dbapi_conn, connection_record, exception):
    """Called when a connection is invalidated (marked as bad)."""
    pool_health.record_error("invalidate")
    if exception:
        logger.warning(f"Connection invalidated: {exception}")


@event.listens_for(Pool, "reset")
def on_reset(dbapi_conn, connection_record):
    """Called when a connection is reset before being returned to pool."""
    pass  # Just monitoring, no action needed


# ============================================================================
# Circuit Breaker for Database Operations
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern for database operations.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail fast
    - HALF_OPEN: Testing if system recovered
    """
    
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._lock = threading.Lock()
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._success_count = 0
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        with self._lock:
            if self._state == self.OPEN:
                # Check if recovery timeout has passed
                if self._last_failure_time:
                    elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self._state = self.HALF_OPEN
                        self._half_open_calls = 0
                        logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
            return self._state
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        state = self.state
        if state == self.CLOSED:
            return True
        elif state == self.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        else:  # OPEN
            return False
    
    def record_success(self):
        """Record a successful operation."""
        with self._lock:
            self._success_count += 1
            if self._state == self.HALF_OPEN:
                if self._success_count >= self.half_open_max_calls:
                    self._state = self.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' CLOSED after successful recovery")
            elif self._state == self.CLOSED:
                # Fully reset failure count on success to prevent lingering degradation
                self._failure_count = 0
    
    def record_failure(self, error: Optional[Exception] = None):
        """Record a failed operation."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            if self._state == self.HALF_OPEN:
                # Any failure in half-open goes back to open
                self._state = self.OPEN
                logger.warning(f"Circuit breaker '{self.name}' back to OPEN after failure in HALF_OPEN")
            elif self._state == self.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = self.OPEN
                    logger.warning(
                        f"Circuit breaker '{self.name}' OPENED after {self._failure_count} failures"
                    )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self._state,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure": self._last_failure_time.isoformat() if self._last_failure_time else None,
            }
    
    def reset(self):
        """Manually reset the circuit breaker to closed state."""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")


# Global circuit breaker for scanner database operations
scanner_circuit_breaker = CircuitBreaker(
    name="scanner_db",
    failure_threshold=5,
    recovery_timeout=30,
    half_open_max_calls=3
)


# ============================================================================
# Database Session Management Functions
# ============================================================================

def init_db() -> None:
    """Initialize database schema (create all tables).
    
    Note: This is idempotent - it only creates tables/indexes that don't exist.
    Safe to call multiple times.
    """
    from releaseradar.db.models import Base
    
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database schema initialized successfully")
    except Exception as e:
        logger.warning(f"Database schema initialization had issues (likely already exists): {e}")


def get_db() -> Session:
    """
    Get a database session.
    
    Returns:
        SQLAlchemy session instance
        
    Note:
        Caller is responsible for closing the session with close_db()
        or using get_db_context() context manager.
    """
    return SessionLocal()


def close_db() -> None:
    """Close and remove the current database session."""
    SessionLocal.remove()


def close_db_session(db: Session) -> None:
    """Properly close a database session and remove from registry.
    
    Args:
        db: Session instance to close
        
    Note:
        This is the correct way to close sessions from get_db().
        Prevents "idle in transaction" by calling both close() and remove().
        Handles async race conditions gracefully.
    """
    from sqlalchemy.exc import IllegalStateChangeError
    
    try:
        db.close()
    except IllegalStateChangeError:
        # Session already closed or in invalid state - ignore
        pass
    except Exception:
        # Other errors during close - ignore to prevent masking original errors
        pass
    
    try:
        SessionLocal.remove()
    except IllegalStateChangeError:
        # Session registry in invalid state - ignore
        pass
    except Exception:
        pass


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Get a database session as a context manager.
    
    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    
    Yields:
        SQLAlchemy session instance
        
    The session is automatically committed on success and rolled back on error.
    """
    db = get_db()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise
    finally:
        close_db()


@contextmanager
def get_db_transaction() -> Generator[Session, None, None]:
    """
    Get a database session with explicit transaction control.
    
    Usage:
        with get_db_transaction() as db:
            user = User(email="test@example.com")
            db.add(user)
            # Transaction automatically committed on success
    
    Yields:
        SQLAlchemy session instance with transaction
        
    The transaction is automatically committed on success and rolled back on error.
    """
    db = get_db()
    try:
        yield db
        db.commit()
        logger.debug("Database transaction committed")
    except Exception as e:
        db.rollback()
        logger.error(f"Database transaction rolled back: {e}")
        raise DatabaseError(f"Transaction failed: {e}")
    finally:
        close_db()


@contextmanager
def get_scanner_db_context(scanner_key: str = "unknown") -> Generator[Session, None, None]:
    """
    Get a database session with enhanced error handling for scanner operations.
    
    Features:
    - Circuit breaker protection
    - Automatic transaction rollback on any error
    - Connection pool health monitoring
    - Timeout handling
    
    Args:
        scanner_key: Scanner identifier for logging and metrics
        
    Yields:
        SQLAlchemy session instance
        
    Raises:
        DatabaseError: If circuit breaker is open or operation fails
    """
    # Check circuit breaker
    if not scanner_circuit_breaker.can_execute():
        logger.warning(f"Circuit breaker OPEN for scanner '{scanner_key}', skipping database operation")
        raise DatabaseError(
            f"Database operations temporarily disabled for scanner '{scanner_key}'. "
            f"Circuit breaker is {scanner_circuit_breaker.state}."
        )
    
    # Check pool health and attempt recovery if needed
    if not pool_health.is_healthy():
        logger.warning(f"Connection pool unhealthy, attempting recovery for scanner '{scanner_key}'")
        if not pool_health.attempt_recovery():
            scanner_circuit_breaker.record_failure()
            raise DatabaseError(
                f"Connection pool recovery failed for scanner '{scanner_key}'"
            )
    
    db = None
    start_time = time.time()
    
    try:
        db = get_db()
        yield db
        db.commit()
        
        # Record success
        scanner_circuit_breaker.record_success()
        pool_health.mark_healthy()
        
        elapsed = time.time() - start_time
        if elapsed > 10:
            logger.warning(f"Scanner '{scanner_key}' database operation took {elapsed:.2f}s")
            
    except OperationalError as e:
        # Connection-level errors (timeout, lost connection, etc.)
        if db:
            try:
                db.rollback()
            except Exception:
                pass  # Rollback may fail if connection is dead
        
        scanner_circuit_breaker.record_failure(e)
        pool_health.record_error("operational_error")
        
        logger.error(f"Scanner '{scanner_key}' database operational error: {e}")
        raise DatabaseError(f"Database connection error for scanner '{scanner_key}': {e}")
        
    except SQLAlchemyError as e:
        # Other SQLAlchemy errors (integrity, programming, etc.)
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        
        # Don't trigger circuit breaker for non-connection errors
        logger.error(f"Scanner '{scanner_key}' database error: {e}")
        raise DatabaseError(f"Database error for scanner '{scanner_key}': {e}")
        
    except Exception as e:
        # Unexpected errors - rollback and log
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        
        logger.error(f"Scanner '{scanner_key}' unexpected error: {e}")
        raise
        
    finally:
        if db:
            try:
                close_db_session(db)
            except Exception as e:
                logger.warning(f"Error closing database session for scanner '{scanner_key}': {e}")


def check_db_health() -> Dict[str, Any]:
    """
    Perform a comprehensive database health check.
    
    Returns:
        Health check results including connection status, pool stats, and latency
    """
    result = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "connection_test": None,
        "latency_ms": None,
        "pool_stats": None,
        "circuit_breaker": None,
        "errors": [],
    }
    
    # Test connection
    start_time = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        result["connection_test"] = "passed"
        result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    except Exception as e:
        result["status"] = "unhealthy"
        result["connection_test"] = "failed"
        result["errors"].append(f"Connection test failed: {str(e)}")
    
    # Get pool stats
    result["pool_stats"] = pool_health.get_stats()
    result["circuit_breaker"] = scanner_circuit_breaker.get_stats()
    
    # Check if pool is healthy
    if not pool_health.is_healthy():
        result["status"] = "degraded"
        result["errors"].append("Connection pool marked as unhealthy")
    
    # Check circuit breaker
    if scanner_circuit_breaker.state != CircuitBreaker.CLOSED:
        result["status"] = "degraded"
        result["errors"].append(f"Circuit breaker is {scanner_circuit_breaker.state}")
    
    return result


def reset_db_connections() -> bool:
    """
    Reset all database connections and health monitors.
    
    Use this to recover from stuck connections or pool exhaustion.
    
    Returns:
        True if reset was successful
    """
    try:
        logger.info("Resetting database connections...")
        
        # Dispose all connections
        engine.dispose()
        
        # Reset health monitors
        pool_health.mark_healthy()
        scanner_circuit_breaker.reset()
        
        # Test new connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("Database connections reset successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset database connections: {e}")
        return False


def cleanup_idle_transactions():
    """
    Clean up any idle transactions that may be blocking.
    
    This is a maintenance function that should be called periodically
    to prevent transaction accumulation.
    """
    try:
        with engine.connect() as conn:
            # Find and terminate idle transactions older than 5 minutes
            result = conn.execute(text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE state = 'idle in transaction'
                AND query_start < NOW() - INTERVAL '5 minutes'
                AND pid <> pg_backend_pid()
            """))
            terminated = result.rowcount
            conn.commit()
            
            if terminated > 0:
                logger.warning(f"Terminated {terminated} idle transactions")
            
            return terminated
            
    except Exception as e:
        logger.error(f"Failed to cleanup idle transactions: {e}")
        return 0
