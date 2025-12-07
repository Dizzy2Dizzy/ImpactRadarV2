"""
Forum Router for Impact Radar Community Chat

Provides endpoints for Discord-style community chat with @Quant AI integration.
Access restricted to Pro and Team plan users only.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List, ForwardRef
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
import re

from ai.radarquant import RadarQuantOrchestrator
from api.utils.auth import get_current_user_id
from api.utils.paywall import require_plan
from api.ratelimit import limiter
from releaseradar.db.session import get_db
from database import close_db_session
from releaseradar.db.models import User, ForumMessage, ForumReaction, UserNotification
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import joinedload


router = APIRouter(prefix="/forum", tags=["forum"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserInfo(BaseModel):
    """User information for forum display"""
    id: int
    email: str
    username: str
    plan: str
    avatar_url: Optional[str] = None


class ReactionInfo(BaseModel):
    """Reaction information"""
    emoji: str
    count: int
    user_ids: List[int]


class ForumMessageResponse(BaseModel):
    """Forum message with user info"""
    id: int
    content: str
    image_url: Optional[str] = None
    is_ai_response: bool
    ai_prompt: Optional[str] = None
    parent_message_id: Optional[int] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    user: UserInfo
    reactions: List[ReactionInfo] = []
    reply_to: Optional["ForumMessageResponse"] = None

    class Config:
        from_attributes = True


ForumMessageResponse.model_rebuild()


class CreateMessageRequest(BaseModel):
    """Request to create a new forum message"""
    content: str = Field("", max_length=4000, description="Message content")
    image_url: Optional[str] = Field(None, max_length=2000, description="Image or GIF URL")
    parent_message_id: Optional[int] = Field(None, description="ID of message being replied to")
    
    @model_validator(mode='after')
    def validate_has_content_or_image(self):
        if not self.content and not self.image_url:
            raise ValueError('Either content or image_url must be provided')
        return self


class EditMessageRequest(BaseModel):
    """Request to edit a forum message"""
    content: str = Field(..., min_length=1, max_length=4000, description="Updated message content")


class AddReactionRequest(BaseModel):
    """Request to add a reaction to a message"""
    emoji: str = Field(..., min_length=1, max_length=32, description="Emoji code")


class ForumMessagesResponse(BaseModel):
    """Paginated forum messages response"""
    messages: List[ForumMessageResponse]
    total: int
    has_more: bool


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_quant_query(content: str) -> Optional[str]:
    """
    Extract @Quant query from message content.
    Returns the query text after @Quant mention, or None if no mention.
    """
    pattern = r'@[Qq]uant\s+(.+)'
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def get_user_info(user: User) -> UserInfo:
    """Convert User model to UserInfo response"""
    email = user.email or ""
    username = email.split('@')[0] if email else f"user_{user.id}"
    return UserInfo(
        id=user.id,
        email=email,
        username=username,
        plan=user.plan or "free",
        avatar_url=None
    )


def get_quant_user_info() -> UserInfo:
    """Get user info for @Quant AI assistant"""
    return UserInfo(
        id=0,
        email="quant@impactradar.com",
        username="Quant",
        plan="ai",
        avatar_url=None
    )


def extract_mentions(content: str) -> List[str]:
    """
    Extract @username mentions from message content.
    Returns list of unique usernames (without the @ symbol).
    Excludes @Quant which is handled separately for AI responses.
    """
    pattern = r'@([a-zA-Z0-9_]+)'
    matches = re.findall(pattern, content)
    unique_mentions = list(set(matches))
    return [m for m in unique_mentions if m.lower() != 'quant']


def create_mention_notifications(db, mentioner_username: str, content: str, mentioned_usernames: List[str]):
    """
    Create UserNotification records for each mentioned user.
    
    Args:
        db: Database session
        mentioner_username: Username of the person who sent the message
        content: Message content for excerpt
        mentioned_usernames: List of usernames that were @mentioned
    """
    if not mentioned_usernames:
        return
    
    excerpt = content[:100] + "..." if len(content) > 100 else content
    
    for username in mentioned_usernames:
        email_pattern = f"{username}@%"
        mentioned_user = db.query(User).filter(
            User.email.ilike(email_pattern)
        ).first()
        
        if mentioned_user:
            notification = UserNotification(
                user_id=mentioned_user.id,
                title="You were mentioned",
                body=f"@{mentioner_username} mentioned you: \"{excerpt}\"",
                url="/forum"
            )
            db.add(notification)


async def process_quant_response(
    message_id: int,
    query: str,
    user_id: int
):
    """
    Background task to process @Quant AI response.
    Creates a new message with the AI response.
    """
    db = get_db()
    try:
        orchestrator = RadarQuantOrchestrator()
        result = orchestrator.ask(
            question=query,
            user_id=user_id,
            portfolio_focus=True  # Enable full portfolio access for AI responses
        )
        
        ai_response = result.get("answer", "I'm sorry, I couldn't process that request.")
        
        ai_message = ForumMessage(
            user_id=user_id,
            content=ai_response,
            is_ai_response=True,
            ai_prompt=query,
            parent_message_id=message_id
        )
        db.add(ai_message)
        db.commit()
        
    except Exception as e:
        error_message = ForumMessage(
            user_id=user_id,
            content=f"Sorry, I encountered an error processing your request. Please try again later.",
            is_ai_response=True,
            ai_prompt=query,
            parent_message_id=message_id
        )
        db.add(error_message)
        db.commit()
    finally:
        close_db_session(db)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/messages", response_model=ForumMessagesResponse)
async def get_messages(
    limit: int = 50,
    before_id: Optional[int] = None,
    user_id: int = Depends(get_current_user_id)
):
    """
    Get forum messages with pagination.
    
    Access restricted to Pro and Team plan users only.
    Returns messages in reverse chronological order (newest first).
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.plan not in ["pro", "team", "admin", "enterprise"]:
            raise HTTPException(
                status_code=403,
                detail="Forum access requires Pro or Team plan. Upgrade to join the community."
            )
        
        query = db.query(ForumMessage).filter(
            ForumMessage.deleted_at.is_(None)
        ).options(
            joinedload(ForumMessage.user),
            joinedload(ForumMessage.reactions)
        )
        
        if before_id:
            query = query.filter(ForumMessage.id < before_id)
        
        total = db.query(func.count(ForumMessage.id)).filter(
            ForumMessage.deleted_at.is_(None)
        ).scalar()
        
        messages_db = query.order_by(desc(ForumMessage.created_at)).limit(limit + 1).all()
        
        has_more = len(messages_db) > limit
        messages_db = messages_db[:limit]
        
        parent_ids = [msg.parent_message_id for msg in messages_db if msg.parent_message_id]
        parent_messages = {}
        if parent_ids:
            parents = db.query(ForumMessage).filter(
                ForumMessage.id.in_(parent_ids),
                ForumMessage.deleted_at.is_(None)
            ).options(joinedload(ForumMessage.user)).all()
            parent_messages = {p.id: p for p in parents}
        
        messages = []
        for msg in messages_db:
            if msg.is_ai_response:
                user_info = get_quant_user_info()
            else:
                user_info = get_user_info(msg.user)
            
            reaction_counts = {}
            for reaction in msg.reactions:
                if reaction.emoji not in reaction_counts:
                    reaction_counts[reaction.emoji] = {"count": 0, "user_ids": []}
                reaction_counts[reaction.emoji]["count"] += 1
                reaction_counts[reaction.emoji]["user_ids"].append(reaction.user_id)
            
            reactions = [
                ReactionInfo(emoji=emoji, count=data["count"], user_ids=data["user_ids"])
                for emoji, data in reaction_counts.items()
            ]
            
            reply_to = None
            if msg.parent_message_id and msg.parent_message_id in parent_messages:
                parent_msg = parent_messages[msg.parent_message_id]
                if parent_msg.is_ai_response:
                    parent_user_info = get_quant_user_info()
                else:
                    parent_user_info = get_user_info(parent_msg.user)
                reply_to = ForumMessageResponse(
                    id=parent_msg.id,
                    content=parent_msg.content,
                    image_url=parent_msg.image_url,
                    is_ai_response=parent_msg.is_ai_response,
                    ai_prompt=parent_msg.ai_prompt,
                    parent_message_id=parent_msg.parent_message_id,
                    created_at=parent_msg.created_at,
                    edited_at=parent_msg.edited_at,
                    user=parent_user_info,
                    reactions=[],
                    reply_to=None
                )
            
            messages.append(ForumMessageResponse(
                id=msg.id,
                content=msg.content,
                image_url=msg.image_url,
                is_ai_response=msg.is_ai_response,
                ai_prompt=msg.ai_prompt,
                parent_message_id=msg.parent_message_id,
                created_at=msg.created_at,
                edited_at=msg.edited_at,
                user=user_info,
                reactions=reactions,
                reply_to=reply_to
            ))
        
        messages.reverse()
        
        return ForumMessagesResponse(
            messages=messages,
            total=total,
            has_more=has_more
        )
        
    finally:
        close_db_session(db)


@router.post("/messages", response_model=ForumMessageResponse)
async def create_message(
    request: CreateMessageRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id)
):
    """
    Create a new forum message.
    
    If the message contains @Quant mention, triggers AI response in background.
    If the message contains @username mentions, creates notifications for mentioned users.
    Access restricted to Pro and Team plan users only.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.plan not in ["pro", "team", "admin", "enterprise"]:
            raise HTTPException(
                status_code=403,
                detail="Forum access requires Pro or Team plan. Upgrade to join the community."
            )
        
        message = ForumMessage(
            user_id=user_id,
            content=request.content,
            image_url=request.image_url,
            parent_message_id=request.parent_message_id,
            is_ai_response=False
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        
        mentioner_username = user.email.split('@')[0] if user.email else f"user_{user.id}"
        mentioned_usernames = extract_mentions(request.content)
        create_mention_notifications(db, mentioner_username, request.content, mentioned_usernames)
        db.commit()
        
        quant_query = extract_quant_query(request.content)
        if quant_query:
            background_tasks.add_task(
                process_quant_response,
                message.id,
                quant_query,
                user_id
            )
        
        reply_to = None
        if request.parent_message_id:
            parent_msg = db.query(ForumMessage).filter(
                ForumMessage.id == request.parent_message_id,
                ForumMessage.deleted_at.is_(None)
            ).options(joinedload(ForumMessage.user)).first()
            
            if parent_msg:
                if parent_msg.is_ai_response:
                    parent_user_info = get_quant_user_info()
                else:
                    parent_user_info = get_user_info(parent_msg.user)
                
                reply_to = ForumMessageResponse(
                    id=parent_msg.id,
                    content=parent_msg.content,
                    image_url=parent_msg.image_url,
                    is_ai_response=parent_msg.is_ai_response,
                    ai_prompt=parent_msg.ai_prompt,
                    parent_message_id=parent_msg.parent_message_id,
                    created_at=parent_msg.created_at,
                    edited_at=parent_msg.edited_at,
                    user=parent_user_info,
                    reactions=[],
                    reply_to=None
                )
        
        return ForumMessageResponse(
            id=message.id,
            content=message.content,
            image_url=message.image_url,
            is_ai_response=message.is_ai_response,
            ai_prompt=message.ai_prompt,
            parent_message_id=message.parent_message_id,
            created_at=message.created_at,
            edited_at=message.edited_at,
            user=get_user_info(user),
            reactions=[],
            reply_to=reply_to
        )
        
    finally:
        close_db_session(db)


@router.put("/messages/{message_id}", response_model=ForumMessageResponse)
async def edit_message(
    message_id: int,
    request: EditMessageRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Edit a forum message.
    
    Only the message author can edit their own messages.
    AI responses cannot be edited.
    """
    db = get_db()
    try:
        message = db.query(ForumMessage).filter(
            ForumMessage.id == message_id,
            ForumMessage.deleted_at.is_(None)
        ).first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if message.user_id != user_id:
            raise HTTPException(status_code=403, detail="You can only edit your own messages")
        
        if message.is_ai_response:
            raise HTTPException(status_code=403, detail="AI responses cannot be edited")
        
        message.content = request.content
        message.edited_at = datetime.utcnow()
        db.commit()
        db.refresh(message)
        
        user = db.query(User).filter(User.id == user_id).first()
        
        return ForumMessageResponse(
            id=message.id,
            content=message.content,
            image_url=message.image_url,
            is_ai_response=message.is_ai_response,
            ai_prompt=message.ai_prompt,
            parent_message_id=message.parent_message_id,
            created_at=message.created_at,
            edited_at=message.edited_at,
            user=get_user_info(user),
            reactions=[],
            reply_to=None
        )
        
    finally:
        close_db_session(db)


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    user_id: int = Depends(get_current_user_id)
):
    """
    Delete a forum message (soft delete).
    
    Only the message author can delete their own messages.
    """
    db = get_db()
    try:
        message = db.query(ForumMessage).filter(
            ForumMessage.id == message_id,
            ForumMessage.deleted_at.is_(None)
        ).first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if message.user_id != user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="You can only delete your own messages")
        
        message.deleted_at = datetime.utcnow()
        db.commit()
        
        return {"success": True, "message": "Message deleted"}
        
    finally:
        close_db_session(db)


@router.post("/messages/{message_id}/reactions")
async def add_reaction(
    message_id: int,
    request: AddReactionRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Add a reaction to a forum message.
    
    Users can only add one reaction of each emoji type per message.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.plan not in ["pro", "team", "admin", "enterprise"]:
            raise HTTPException(
                status_code=403,
                detail="Forum access requires Pro or Team plan"
            )
        
        message = db.query(ForumMessage).filter(
            ForumMessage.id == message_id,
            ForumMessage.deleted_at.is_(None)
        ).first()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        existing = db.query(ForumReaction).filter(
            ForumReaction.message_id == message_id,
            ForumReaction.user_id == user_id,
            ForumReaction.emoji == request.emoji
        ).first()
        
        if existing:
            db.delete(existing)
            db.commit()
            return {"success": True, "action": "removed"}
        
        reaction = ForumReaction(
            message_id=message_id,
            user_id=user_id,
            emoji=request.emoji
        )
        db.add(reaction)
        db.commit()
        
        return {"success": True, "action": "added"}
        
    finally:
        close_db_session(db)


@router.get("/stats")
async def get_forum_stats(
    user_id: int = Depends(get_current_user_id)
):
    """
    Get forum statistics.
    
    Returns total messages, active users, etc.
    """
    db = get_db()
    try:
        total_messages = db.query(func.count(ForumMessage.id)).filter(
            ForumMessage.deleted_at.is_(None)
        ).scalar()
        
        active_users = db.query(func.count(func.distinct(ForumMessage.user_id))).filter(
            ForumMessage.deleted_at.is_(None)
        ).scalar()
        
        ai_responses = db.query(func.count(ForumMessage.id)).filter(
            ForumMessage.deleted_at.is_(None),
            ForumMessage.is_ai_response == True
        ).scalar()
        
        return {
            "total_messages": total_messages,
            "active_users": active_users,
            "ai_responses": ai_responses
        }
        
    finally:
        close_db_session(db)


@router.get("/access")
async def check_forum_access(
    user_id: int = Depends(get_current_user_id)
):
    """
    Check if user has forum access.
    
    Returns access status and user plan information.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        has_access = user.plan in ["pro", "team", "admin", "enterprise"]
        
        return {
            "has_access": has_access,
            "plan": user.plan,
            "message": None if has_access else "Upgrade to Pro or Team plan to access the community forum."
        }
        
    finally:
        close_db_session(db)


class ForumUserResponse(BaseModel):
    """User info for @mention autocomplete"""
    id: int
    username: str
    plan: str


@router.get("/users", response_model=List[ForumUserResponse])
async def get_forum_users(
    user_id: int = Depends(get_current_user_id)
):
    """
    Get list of forum users for @mention autocomplete.
    
    Returns users with Pro, Team, Admin, or Enterprise plans.
    Only accessible to users with forum access.
    """
    db = get_db()
    try:
        current_user = db.query(User).filter(User.id == user_id).first()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if current_user.plan not in ["pro", "team", "admin", "enterprise"]:
            raise HTTPException(
                status_code=403,
                detail="Forum access requires Pro or Team plan"
            )
        
        users = db.query(User).filter(
            User.plan.in_(["pro", "team", "admin", "enterprise"]),
            User.email.isnot(None)
        ).all()
        
        return [
            ForumUserResponse(
                id=u.id,
                username=u.email.split('@')[0] if u.email else f"user_{u.id}",
                plan=u.plan or "free"
            )
            for u in users
        ]
        
    finally:
        close_db_session(db)
