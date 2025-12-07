"""Authentication router"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

from api.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from api.dependencies import get_db
from api.utils.auth import hash_password, verify_password, create_access_token, get_current_user_with_plan
from api.config import settings
from api.ratelimit import limiter
from database import User

router = APIRouter(prefix="/auth", tags=["authentication"])


class ProfileUpdateRequest(BaseModel):
    """Request model for profile update"""
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class ProfileResponse(BaseModel):
    """Response model for profile"""
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    email: str
    plan: str


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user and return access token (rate limited: 5 registrations per minute)"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        is_verified=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create access token for immediate login
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id, "plan": new_user.plan},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token (rate limited: 10 attempts per minute)"""
    # Find user
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "plan": user.plan},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout():
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Get the current user's profile"""
    user_id = user_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return ProfileResponse(
        username=user.username,
        avatar_url=user.avatar_url,
        email=user.email,
        plan=user.plan
    )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Update the current user's profile (username and avatar)"""
    user_id = user_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update profile fields
    if profile_data.username is not None:
        user.username = profile_data.username
    if profile_data.avatar_url is not None:
        user.avatar_url = profile_data.avatar_url
    
    db.commit()
    db.refresh(user)
    
    return ProfileResponse(
        username=user.username,
        avatar_url=user.avatar_url,
        email=user.email,
        plan=user.plan
    )
