"""
Playbook Service - CRUD operations and matching logic for trading playbooks.

Handles playbook management, rule evaluation, and event-to-playbook matching.
"""

from datetime import datetime
from typing import Any, Optional
import re

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from releaseradar.db.models import (
    Playbook,
    PlaybookScreenshot,
    PlaybookRule,
    EventPlaybookMatch,
    Event,
)


class PlaybookService:
    """Service for managing playbooks and their rules."""

    def __init__(self, session: Session):
        self.session = session

    def get_all_playbooks(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        visibility: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get all playbooks with optional filters."""
        query = self.session.query(Playbook).options(
            joinedload(Playbook.screenshots),
            joinedload(Playbook.rules),
        )

        if is_active is not None:
            query = query.filter(Playbook.is_active == is_active)

        if category:
            query = query.filter(Playbook.category == category)

        if visibility:
            query = query.filter(Playbook.visibility == visibility)

        query = query.order_by(Playbook.display_order, Playbook.title)
        playbooks = query.offset(offset).limit(limit).all()

        return [self._playbook_to_dict(p) for p in playbooks]

    def get_playbook_by_id(self, playbook_id: int) -> Optional[dict]:
        """Get a single playbook by ID."""
        playbook = (
            self.session.query(Playbook)
            .options(
                joinedload(Playbook.screenshots),
                joinedload(Playbook.rules),
            )
            .filter(Playbook.id == playbook_id)
            .first()
        )
        return self._playbook_to_dict(playbook) if playbook else None

    def get_playbook_by_slug(self, slug: str) -> Optional[dict]:
        """Get a single playbook by slug."""
        playbook = (
            self.session.query(Playbook)
            .options(
                joinedload(Playbook.screenshots),
                joinedload(Playbook.rules),
            )
            .filter(Playbook.slug == slug)
            .first()
        )
        return self._playbook_to_dict(playbook) if playbook else None

    def create_playbook(self, data: dict) -> dict:
        """Create a new playbook."""
        playbook = Playbook(
            slug=data["slug"],
            title=data["title"],
            category=data["category"],
            description=data.get("description"),
            setup_conditions=data.get("setup_conditions", {}),
            entry_logic=data["entry_logic"],
            stop_template=data.get("stop_template"),
            target_template=data.get("target_template"),
            holding_period=data.get("holding_period"),
            win_rate=data.get("win_rate"),
            avg_r=data.get("avg_r"),
            sample_size=data.get("sample_size", 0),
            stats_metadata=data.get("stats_metadata"),
            display_order=data.get("display_order", 0),
            is_active=data.get("is_active", True),
            is_featured=data.get("is_featured", False),
            author_id=data.get("author_id"),
            visibility=data.get("visibility", "public"),
        )
        self.session.add(playbook)
        self.session.flush()

        if "rules" in data:
            for rule_data in data["rules"]:
                rule = PlaybookRule(
                    playbook_id=playbook.id,
                    rule_type=rule_data["rule_type"],
                    operator=rule_data.get("operator", "eq"),
                    value=rule_data["value"],
                    is_required=rule_data.get("is_required", True),
                    weight=rule_data.get("weight", 1.0),
                )
                self.session.add(rule)

        if "screenshots" in data:
            for idx, ss_data in enumerate(data["screenshots"][:3]):
                screenshot = PlaybookScreenshot(
                    playbook_id=playbook.id,
                    slot_index=idx,
                    image_url=ss_data.get("image_url"),
                    caption=ss_data.get("caption"),
                    event_ref=ss_data.get("event_ref"),
                )
                self.session.add(screenshot)

        self.session.commit()
        return self.get_playbook_by_id(playbook.id)

    def update_playbook(self, playbook_id: int, data: dict) -> Optional[dict]:
        """Update an existing playbook."""
        playbook = self.session.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not playbook:
            return None

        for field in [
            "title", "category", "description", "setup_conditions",
            "entry_logic", "stop_template", "target_template", "holding_period",
            "win_rate", "avg_r", "sample_size", "stats_metadata",
            "display_order", "is_active", "is_featured", "visibility"
        ]:
            if field in data:
                setattr(playbook, field, data[field])

        playbook.updated_at = datetime.utcnow()
        self.session.commit()
        return self.get_playbook_by_id(playbook_id)

    def delete_playbook(self, playbook_id: int) -> bool:
        """Delete a playbook."""
        playbook = self.session.query(Playbook).filter(Playbook.id == playbook_id).first()
        if not playbook:
            return False
        self.session.delete(playbook)
        self.session.commit()
        return True

    def add_screenshot(self, playbook_id: int, slot_index: int, image_url: str, caption: Optional[str] = None, event_ref: Optional[int] = None) -> Optional[dict]:
        """Add or update a screenshot slot."""
        existing = self.session.query(PlaybookScreenshot).filter(
            and_(
                PlaybookScreenshot.playbook_id == playbook_id,
                PlaybookScreenshot.slot_index == slot_index
            )
        ).first()

        if existing:
            existing.image_url = image_url
            existing.caption = caption
            existing.event_ref = event_ref
        else:
            screenshot = PlaybookScreenshot(
                playbook_id=playbook_id,
                slot_index=slot_index,
                image_url=image_url,
                caption=caption,
                event_ref=event_ref,
            )
            self.session.add(screenshot)

        self.session.commit()
        return self.get_playbook_by_id(playbook_id)

    def get_playbook_categories(self) -> list[str]:
        """Get all unique playbook categories."""
        result = self.session.query(Playbook.category).distinct().all()
        return [r[0] for r in result if r[0]]

    def _playbook_to_dict(self, playbook: Playbook) -> dict:
        """Convert a Playbook ORM object to a dictionary."""
        if not playbook:
            return None

        return {
            "id": playbook.id,
            "slug": playbook.slug,
            "title": playbook.title,
            "category": playbook.category,
            "description": playbook.description,
            "setup_conditions": playbook.setup_conditions,
            "entry_logic": playbook.entry_logic,
            "stop_template": playbook.stop_template,
            "target_template": playbook.target_template,
            "holding_period": playbook.holding_period,
            "win_rate": playbook.win_rate,
            "avg_r": playbook.avg_r,
            "sample_size": playbook.sample_size,
            "stats_metadata": playbook.stats_metadata,
            "display_order": playbook.display_order,
            "is_active": playbook.is_active,
            "is_featured": playbook.is_featured,
            "visibility": playbook.visibility,
            "author_id": playbook.author_id,
            "created_at": playbook.created_at.isoformat() if playbook.created_at else None,
            "updated_at": playbook.updated_at.isoformat() if playbook.updated_at else None,
            "screenshots": [
                {
                    "id": s.id,
                    "slot_index": s.slot_index,
                    "image_url": s.image_url,
                    "caption": s.caption,
                    "event_ref": s.event_ref,
                }
                for s in (playbook.screenshots or [])
            ],
            "rules": [
                {
                    "id": r.id,
                    "rule_type": r.rule_type,
                    "operator": r.operator,
                    "value": r.value,
                    "is_required": r.is_required,
                    "weight": r.weight,
                }
                for r in (playbook.rules or [])
            ],
        }


class PlaybookMatchingService:
    """Service for matching events to playbooks based on rules."""

    def __init__(self, session: Session):
        self.session = session
        self._playbook_cache: Optional[list] = None
        self._cache_timestamp: float = 0
        self._cache_ttl = 300  # 5 minutes

    def match_event_to_playbooks(self, event: Event, min_confidence: float = 0.5) -> list[dict]:
        """
        Match a single event against all active playbooks.
        Returns list of matching playbooks with confidence scores.
        """
        playbooks = self._get_active_playbooks()
        matches = []

        for playbook in playbooks:
            match_result = self._evaluate_playbook_rules(event, playbook)
            if match_result["confidence"] >= min_confidence:
                matches.append({
                    "playbook_id": playbook.id,
                    "playbook_slug": playbook.slug,
                    "playbook_title": playbook.title,
                    "playbook_category": playbook.category,
                    "confidence": match_result["confidence"],
                    "rules_matched": match_result["rules_matched"],
                })

        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches

    def save_event_matches(self, event_id: int, matches: list[dict], source: str = "auto") -> int:
        """Save event-playbook matches to database."""
        count = 0
        for match in matches:
            existing = self.session.query(EventPlaybookMatch).filter(
                and_(
                    EventPlaybookMatch.event_id == event_id,
                    EventPlaybookMatch.playbook_id == match["playbook_id"]
                )
            ).first()

            if existing:
                existing.confidence = match["confidence"]
                existing.rules_matched = match["rules_matched"]
                existing.match_source = source
            else:
                new_match = EventPlaybookMatch(
                    event_id=event_id,
                    playbook_id=match["playbook_id"],
                    match_source=source,
                    confidence=match["confidence"],
                    rules_matched=match["rules_matched"],
                )
                self.session.add(new_match)
                count += 1

        self.session.commit()
        return count

    def get_event_playbook_matches(self, event_id: int) -> list[dict]:
        """Get all playbook matches for an event."""
        matches = (
            self.session.query(EventPlaybookMatch)
            .options(joinedload(EventPlaybookMatch.playbook))
            .filter(EventPlaybookMatch.event_id == event_id)
            .order_by(EventPlaybookMatch.confidence.desc())
            .all()
        )

        return [
            {
                "id": m.id,
                "playbook_id": m.playbook_id,
                "playbook_slug": m.playbook.slug if m.playbook else None,
                "playbook_title": m.playbook.title if m.playbook else None,
                "playbook_category": m.playbook.category if m.playbook else None,
                "match_source": m.match_source,
                "confidence": m.confidence,
                "rules_matched": m.rules_matched,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in matches
        ]

    def get_playbook_matched_events(self, playbook_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get events that match a specific playbook."""
        matches = (
            self.session.query(EventPlaybookMatch)
            .options(joinedload(EventPlaybookMatch.event))
            .filter(EventPlaybookMatch.playbook_id == playbook_id)
            .order_by(EventPlaybookMatch.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "match_id": m.id,
                "event_id": m.event_id,
                "confidence": m.confidence,
                "match_source": m.match_source,
                "event": {
                    "id": m.event.id,
                    "ticker": m.event.ticker,
                    "title": m.event.title,
                    "event_type": m.event.event_type,
                    "date": m.event.date.isoformat() if m.event.date else None,
                    "impact_score": m.event.impact_score,
                    "direction": m.event.direction,
                    "realized_return_1d": m.event.realized_return_1d,
                } if m.event else None,
            }
            for m in matches
        ]

    def batch_match_events(self, event_ids: list[int], min_confidence: float = 0.5) -> dict:
        """Match multiple events to playbooks in batch."""
        events = self.session.query(Event).filter(Event.id.in_(event_ids)).all()
        results = {"matched": 0, "total": len(events)}

        for event in events:
            matches = self.match_event_to_playbooks(event, min_confidence)
            if matches:
                self.save_event_matches(event.id, matches)
                results["matched"] += 1

        return results

    def _get_active_playbooks(self) -> list[Playbook]:
        """Get all active playbooks with their rules (cached)."""
        import time
        now = time.time()

        if self._playbook_cache is None or (now - self._cache_timestamp) > self._cache_ttl:
            self._playbook_cache = (
                self.session.query(Playbook)
                .options(joinedload(Playbook.rules))
                .filter(Playbook.is_active == True)
                .all()
            )
            self._cache_timestamp = now

        return self._playbook_cache

    def _evaluate_playbook_rules(self, event: Event, playbook: Playbook) -> dict:
        """Evaluate all rules for a playbook against an event."""
        rules = playbook.rules or []
        if not rules:
            return {"confidence": 0.0, "rules_matched": []}

        total_weight = 0.0
        matched_weight = 0.0
        matched_rules = []
        required_failed = False

        for rule in rules:
            total_weight += rule.weight
            is_match = self._evaluate_single_rule(event, rule)

            if is_match:
                matched_weight += rule.weight
                matched_rules.append({
                    "rule_type": rule.rule_type,
                    "operator": rule.operator,
                    "value": rule.value,
                })
            elif rule.is_required:
                required_failed = True

        if required_failed:
            return {"confidence": 0.0, "rules_matched": []}

        confidence = matched_weight / total_weight if total_weight > 0 else 0.0
        return {"confidence": confidence, "rules_matched": matched_rules}

    def _evaluate_single_rule(self, event: Event, rule: PlaybookRule) -> bool:
        """Evaluate a single rule against an event."""
        rule_type = rule.rule_type
        operator = rule.operator
        value = rule.value

        if rule_type == "event_type":
            event_value = event.event_type
            return self._compare(event_value, operator, value)

        elif rule_type == "sector":
            event_value = event.sector
            return self._compare(event_value, operator, value)

        elif rule_type == "direction":
            event_value = event.direction
            return self._compare(event_value, operator, value)

        elif rule_type == "score_range":
            event_value = event.impact_score or 0
            if isinstance(value, list) and len(value) == 2:
                return value[0] <= event_value <= value[1]
            return False

        elif rule_type == "keyword":
            text = f"{event.title or ''} {event.description or ''}".lower()
            if isinstance(value, list):
                return any(kw.lower() in text for kw in value)
            return str(value).lower() in text

        elif rule_type == "market_cap":
            return True

        elif rule_type == "info_tier":
            event_value = event.info_tier
            return self._compare(event_value, operator, value)

        return False

    def _compare(self, event_value: Any, operator: str, rule_value: Any) -> bool:
        """Compare event value against rule value using the specified operator."""
        if event_value is None:
            return False

        if operator == "eq":
            if isinstance(rule_value, list):
                return event_value in rule_value
            return event_value == rule_value

        elif operator == "ne":
            if isinstance(rule_value, list):
                return event_value not in rule_value
            return event_value != rule_value

        elif operator == "in":
            if isinstance(rule_value, list):
                return event_value in rule_value
            return event_value == rule_value

        elif operator == "contains":
            if isinstance(event_value, str) and isinstance(rule_value, str):
                return rule_value.lower() in event_value.lower()
            return False

        elif operator == "gt":
            try:
                return float(event_value) > float(rule_value)
            except (ValueError, TypeError):
                return False

        elif operator == "gte":
            try:
                return float(event_value) >= float(rule_value)
            except (ValueError, TypeError):
                return False

        elif operator == "lt":
            try:
                return float(event_value) < float(rule_value)
            except (ValueError, TypeError):
                return False

        elif operator == "lte":
            try:
                return float(event_value) <= float(rule_value)
            except (ValueError, TypeError):
                return False

        return False

    def clear_cache(self):
        """Clear the playbook cache."""
        self._playbook_cache = None
        self._cache_timestamp = 0
