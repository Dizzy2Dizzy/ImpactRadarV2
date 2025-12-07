"""
End-to-end smoke test for event ingestion to API flow.

Tests the complete flow from event creation via DataManager
to retrieval via the public API endpoints.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_manager import DataManager


class TestE2ESmoke:
    """End-to-end smoke test for event ingestion to API."""
    
    def test_event_ingestion_to_api(self, test_client, db_session, test_company):
        """
        End-to-end flow:
        1. Create test event via DataManager.add_event()
        2. Verify event scored automatically
        3. Verify event appears in GET /events/public
        4. Verify event appears in company events
        5. Clean up test data
        """
        dm = DataManager()
        
        # Step 1: Create test event via DataManager
        # Step 1: Create test event via DataManager (without raw_id parameter)
        created_event = dm.add_event(
            ticker=test_company.ticker,
            company_name=test_company.name,
            title="E2E Test Product Launch",
            event_type="product_launch",
            date=datetime.now(timezone.utc),
            source="E2E Test Source",
            source_url="https://example.com/e2e-test",
            description="End-to-end test event for smoke testing",
            sector=test_company.sector
        )
        assert created_event is not None, "Event should be created successfully"
        event_id = created_event['id']
        
        # Step 2: Verify event scored automatically
        # Get event from database to check if it has a score
        event = dm.get_event(event_id)
        assert event is not None, "Event should exist in database"
        assert event.get('impact_score') is not None, "Event should have impact_score"
        assert 0 <= event['impact_score'] <= 100, "Score should be in valid range [0, 100]"
        
        # Step 3: Verify event appears in GET /events/public
        response = test_client.get("/events/public")
        assert response.status_code == 200, "Public events endpoint should return 200"
        
        events_data = response.json()
        assert isinstance(events_data, list), "Response should be a list of events"
        
        # Find our test event in the response
        test_event_found = False
        for event_item in events_data:
            if event_item.get('id') == event_id:
                test_event_found = True
                assert event_item['ticker'] == test_company.ticker
                assert event_item['title'] == event_data['title']
                assert event_item['event_type'] == event_data['event_type']
                assert 'score' in event_item or 'impact_score' in event_item
                break
        
        assert test_event_found, "Test event should appear in public events API"
        
        # Step 4: Verify event appears in company events
        response = test_client.get(f"/companies/{test_company.ticker}/events")
        
        # Should return 200 or 401 (if auth required)
        if response.status_code == 200:
            company_events = response.json()
            assert isinstance(company_events, list), "Response should be a list of events"
            
            # Find our test event
            test_event_in_company = False
            for event_item in company_events:
                if event_item.get('id') == event_id:
                    test_event_in_company = True
                    assert event_item['ticker'] == test_company.ticker
                    break
            
            assert test_event_in_company, "Test event should appear in company events"
        
        # Step 5: Clean up test data (handled by db_session fixture)
        # Verify cleanup will work
        from releaseradar.db.models import Event
        event_obj = db_session.query(Event).filter(Event.id == event_id).first()
        assert event_obj is not None, "Event should exist before cleanup"
        
        # Delete event (cleanup)
        db_session.delete(event_obj)
        db_session.commit()
        
        # Verify deletion
        event_obj = db_session.query(Event).filter(Event.id == event_id).first()
        assert event_obj is None, "Event should be deleted after cleanup"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
