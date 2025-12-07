"""Authentication utilities"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.config import settings
from api.schemas.auth import TokenData

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        plan = payload.get("plan", "free")  # Extract plan, default to free
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(email=str(email), user_id=int(user_id) if user_id else 0, plan=str(plan))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current user from JWT token"""
    token = credentials.credentials
    return decode_access_token(token)


async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session = None
) -> TokenData:
    """
    Dependency to require admin user.
    
    Verifies JWT and checks is_admin flag in database.
    Raises 403 if user is not an admin.
    """
    from api.dependencies import get_db
    from sqlalchemy.orm import Session
    from backend.database import User
    
    # Get current user from token
    user_data = decode_access_token(credentials.credentials)
    
    # Get database session if not provided
    if db_session is None:
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            # Verify admin status in database
            user = db.query(User).filter(User.id == user_data.user_id).first()
            if not user or not bool(user.is_admin):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied, upgrade your plan please."
                )
        finally:
            db_gen.close()
    
    return user_data


async def get_current_user_id(
    request: Request,
    current_user: TokenData = Depends(get_current_user)
) -> int:
    """
    Get current user ID and set plan on request state for rate limiting.
    
    This ensures SlowAPI's plan_limit() can access the user's subscription plan
    for dynamic per-plan burst rate limiting.
    
    Also tracks user activity for real-time active users monitoring.
    """
    if not current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    # Set plan on request state for SlowAPI rate limiting
    plan = current_user.plan if hasattr(current_user, 'plan') else "free"
    request.state.plan = plan
    
    # Track active user for admin monitoring
    from api.routers.admin import active_users_store
    user_email = current_user.email if hasattr(current_user, 'email') else ""
    active_users_store.heartbeat(current_user.user_id, email=user_email or "", plan=plan)
    
    return current_user.user_id


async def get_user_plan(current_user: TokenData = Depends(get_current_user)) -> str:
    """Get current user plan from JWT"""
    return current_user.plan if hasattr(current_user, 'plan') else "free"


async def get_current_user_with_plan(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get current user with effective plan (accounting for expired trials).
    
    Returns tuple of (user_id, effective_plan, trial_ends_at) for use in 
    plan enforcement and usage tracking.
    
    This dependency should be used by endpoints that need plan-based access control.
    """
    from api.dependencies import get_db
    from sqlalchemy.orm import Session
    from backend.releaseradar.db.models import User
    from api.utils.paywall import get_effective_plan
    from api.utils.usage_tracking import track_api_call
    
    # Decode token
    token_data = decode_access_token(credentials.credentials)
    
    if not token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
    
    # Get fresh plan data from database (don't trust JWT claim)
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Calculate effective plan (handles expired trials)
        # Cast SQLAlchemy Column types to Python types for type checker
        user_plan = str(user.plan) if user.plan else "free"
        user_trial_ends = user.trial_ends_at if user.trial_ends_at is not None else None
        effective_plan = get_effective_plan(user_plan, user_trial_ends)  # type: ignore
        
        # Track API call for monthly metering
        track_api_call(effective_plan)
        
        # Track active user for admin monitoring
        from api.routers.admin import active_users_store
        user_id_int = int(str(user.id)) if user.id else 0
        user_email_str = str(user.email) if user.email else ""
        active_users_store.heartbeat(user_id_int, email=user_email_str, plan=effective_plan)
        
        return {
            "user_id": user.id,
            "email": user.email,
            "plan": effective_plan,
            "trial_ends_at": user.trial_ends_at,
            "is_admin": user.is_admin
        }
    finally:
        db_gen.close()


async def get_current_user_optional(
    request: Request
) -> Optional[dict]:
    """
    Optional authentication dependency for endpoints that support both
    authenticated and unauthenticated access.
    
    Returns user data dict if valid JWT is present, None otherwise.
    This allows endpoints to provide personalized data for authenticated users
    while remaining accessible to unauthenticated requests.
    """
    from api.dependencies import get_db
    from sqlalchemy.orm import Session
    from backend.releaseradar.db.models import User
    from api.utils.paywall import get_effective_plan
    
    # Try to extract Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        # Extract and decode token
        token = auth_header.replace("Bearer ", "")
        token_data = decode_access_token(token)
        
        if not token_data.user_id:
            return None
        
        # Get fresh plan data from database
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            user = db.query(User).filter(User.id == token_data.user_id).first()
            if not user:
                return None
            
            # Calculate effective plan
            # Cast SQLAlchemy Column types to Python types for type checker
            user_plan = str(user.plan) if user.plan else "free"
            user_trial_ends = user.trial_ends_at if user.trial_ends_at is not None else None
            effective_plan = get_effective_plan(user_plan, user_trial_ends)  # type: ignore
            
            return {
                "user_id": user.id,
                "email": user.email,
                "plan": effective_plan,
                "trial_ends_at": user.trial_ends_at,
                "is_admin": user.is_admin
            }
        finally:
            db_gen.close()
    except (JWTError, HTTPException):
        # Invalid token - return None for unauthenticated access
        return None

