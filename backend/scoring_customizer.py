"""
Scoring Customizer for Impact Radar

Applies user-specific scoring weights and preferences to event impact scores.
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from database import get_db, close_db_session
from releaseradar.db.models import UserScoringPreference


class ScoringCustomizer:
    """
    Apply user-specific scoring weights and filters to event impact scores.
    """
    
    def apply_user_weights(
        self,
        base_score: int,
        event_type: str,
        sector: Optional[str],
        preferences: Dict
    ) -> int:
        """
        Apply user's custom weights to base impact score.
        
        Args:
            base_score: Original impact score (0-100)
            event_type: Event type (e.g., "fda_approval", "sec_8k")
            sector: Company sector (e.g., "Healthcare", "Technology")
            preferences: User preferences dict with event_type_weights and sector_weights
        
        Returns:
            Adjusted score (clamped 0-100)
        """
        adjusted_score = float(base_score)
        
        # Apply event type weight
        event_type_weights = preferences.get('event_type_weights', {})
        if event_type_weights and event_type in event_type_weights:
            weight = event_type_weights[event_type]
            adjusted_score *= weight
        
        # Apply sector weight
        sector_weights = preferences.get('sector_weights', {})
        if sector_weights and sector and sector in sector_weights:
            weight = sector_weights[sector]
            adjusted_score *= weight
        
        # Clamp to 0-100 range
        return max(0, min(100, int(round(adjusted_score))))
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        Load user preferences from database.
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with event_type_weights, sector_weights, confidence_threshold, min_impact_score
            Returns defaults if no preferences exist
        """
        db = get_db()
        try:
            pref = db.query(UserScoringPreference).filter(
                UserScoringPreference.user_id == user_id
            ).first()
            
            if not pref:
                # Return defaults
                return {
                    'event_type_weights': {},
                    'sector_weights': {},
                    'confidence_threshold': 0.5,
                    'min_impact_score': 0
                }
            
            return {
                'event_type_weights': pref.event_type_weights or {},
                'sector_weights': pref.sector_weights or {},
                'confidence_threshold': pref.confidence_threshold,
                'min_impact_score': pref.min_impact_score
            }
        finally:
            close_db_session(db)
    
    def save_user_preferences(self, user_id: int, preferences: Dict) -> None:
        """
        Save/update user preferences.
        
        Args:
            user_id: User ID
            preferences: Dict with event_type_weights, sector_weights, confidence_threshold, min_impact_score
        """
        db = get_db()
        try:
            pref = db.query(UserScoringPreference).filter(
                UserScoringPreference.user_id == user_id
            ).first()
            
            if pref:
                # Update existing
                pref.event_type_weights = preferences.get('event_type_weights', {})
                pref.sector_weights = preferences.get('sector_weights', {})
                pref.confidence_threshold = preferences.get('confidence_threshold', 0.5)
                pref.min_impact_score = preferences.get('min_impact_score', 0)
            else:
                # Create new
                pref = UserScoringPreference(
                    user_id=user_id,
                    event_type_weights=preferences.get('event_type_weights', {}),
                    sector_weights=preferences.get('sector_weights', {}),
                    confidence_threshold=preferences.get('confidence_threshold', 0.5),
                    min_impact_score=preferences.get('min_impact_score', 0)
                )
                db.add(pref)
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def reset_user_preferences(self, user_id: int) -> None:
        """
        Reset user preferences to defaults (delete custom preferences).
        
        Args:
            user_id: User ID
        """
        db = get_db()
        try:
            pref = db.query(UserScoringPreference).filter(
                UserScoringPreference.user_id == user_id
            ).first()
            
            if pref:
                db.delete(pref)
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
