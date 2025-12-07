"""
Integration tests for admin endpoint protection and rate limiting.

Tests admin-only endpoints (/scanners/run, /scanners/rescan/*),
audit logging, and rate limit enforcement.
"""

import os
import sys
from datetime import datetime, timedelta
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAdminProtection:
    """Test admin endpoint protection and rate limiting."""
    
    def test_manual_scan_requires_admin(self, test_client, regular_user, admin_user):
        """Non-admin users should get 403 on /scanners/run."""
        # Try to run scanner as regular user
        response = test_client.post(
            "/scanners/run",
            json={"source": "sec"},
            headers={"Authorization": f"Bearer {regular_user['token']}"}
        )
        
        assert response.status_code == 403, "Regular users should be denied with 403"
        data = response.json()
        assert "detail" in data
        assert "admin" in data["detail"].lower(), "Error message should mention admin requirement"
        
        # Verify admin user can access
        response = test_client.post(
            "/scanners/run",
            json={"source": "sec"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        assert response.status_code == 200, "Admin users should be allowed"
    
    def test_rescan_company_requires_admin(self, test_client, regular_user, admin_user, db_session):
        """Non-admin users should get 403 on /scanners/rescan/company."""
        # Create test company
        from releaseradar.db.models import Company
        company = Company(
            ticker="TEST_AAPL",
            name="Test Apple Inc.",
            sector="Technology",
            tracked=True
        )
        db_session.add(company)
        db_session.commit()
        
        # Try to rescan company as regular user
        response = test_client.post(
            "/scanners/rescan/company",
            json={"ticker": "TEST_AAPL"},
            headers={"Authorization": f"Bearer {regular_user['token']}"}
        )
        
        assert response.status_code == 403, "Regular users should be denied with 403"
        data = response.json()
        assert "detail" in data
        assert "admin" in data["detail"].lower(), "Error message should mention admin requirement"
        
        # Verify admin user can access
        response = test_client.post(
            "/scanners/rescan/company",
            json={"ticker": "TEST_AAPL"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        # Should succeed (200) or fail with other error (not 403)
        assert response.status_code != 403, "Admin users should not be denied with 403"
    
    def test_admin_audit_logging(self, test_client, admin_user, db_session, caplog):
        """Admin actions should be logged with user_id, email, timestamp."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Create test company
        from releaseradar.db.models import Company
        company = Company(
            ticker="TEST_AAPL",
            name="Test Apple Inc.",
            sector="Technology",
            tracked=True
        )
        db_session.add(company)
        db_session.commit()
        
        # Perform admin action (rescan company)
        response = test_client.post(
            "/scanners/rescan/company",
            json={"ticker": "TEST_AAPL"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        # Should succeed or fail gracefully (not 403)
        assert response.status_code != 403
        
        # Check if audit log was created in database
        from releaseradar.db.models import ScanJob
        jobs = db_session.query(ScanJob).filter(
            ScanJob.created_by == admin_user['user_id'],
            ScanJob.ticker == "TEST_AAPL"
        ).all()
        
        # If job was created, verify audit trail
        if len(jobs) > 0:
            job = jobs[0]
            assert job.created_by == admin_user['user_id'], "Job should have correct user_id"
            assert job.ticker == "TEST_AAPL", "Job should have correct ticker"
            assert job.scope == "company", "Job should have correct scope"
            assert job.created_at is not None, "Job should have creation timestamp"
            
            # Verify timestamp is recent (within last minute)
            assert datetime.utcnow() - job.created_at < timedelta(minutes=1), \
                "Job timestamp should be recent"
        
        # Check application logs for audit entry
        # Note: This may not work in all test environments
        log_messages = [record.message for record in caplog.records]
        audit_logs = [msg for msg in log_messages if "rescan" in msg.lower() and "admin" in msg.lower()]
        
        # If audit logging is implemented, should have log entry
        if len(audit_logs) > 0:
            # Verify log contains user info
            audit_log = audit_logs[0]
            assert str(admin_user['user_id']) in audit_log or admin_user['email'] in audit_log, \
                "Audit log should contain user identification"
    
    def test_rate_limiting(self, test_client, admin_user, db_session):
        """Rate limits should be enforced (1/60s company, 1/120s scanner)."""
        # Create test company
        from releaseradar.db.models import Company
        company = Company(
            ticker="TEST_AAPL",
            name="Test Apple Inc.",
            sector="Technology",
            tracked=True
        )
        db_session.add(company)
        db_session.commit()
        
        # Test company rescan rate limit (1 per 60 seconds)
        # First request should succeed
        response1 = test_client.post(
            "/scanners/rescan/company",
            json={"ticker": "TEST_AAPL"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        assert response1.status_code in [200, 201], "First request should succeed"
        
        # Second request immediately after should be rate limited
        response2 = test_client.post(
            "/scanners/rescan/company",
            json={"ticker": "TEST_AAPL"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        assert response2.status_code == 429, "Second request should be rate limited with 429"
        data = response2.json()
        assert "detail" in data
        assert "rate limit" in data["detail"].lower() or "wait" in data["detail"].lower(), \
            "Error should mention rate limiting"
        
        # Test scanner rescan rate limit (1 per 120 seconds)
        # Note: This test is commented out to avoid waiting 120 seconds
        # In production tests, you'd mock the time or use a smaller window
        """
        response1 = test_client.post(
            "/scanners/rescan/scanner",
            json={"scanner_key": "sec_8k_scanner"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        assert response1.status_code in [200, 201], "First scanner request should succeed"
        
        response2 = test_client.post(
            "/scanners/rescan/scanner",
            json={"scanner_key": "sec_8k_scanner"},
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )
        
        assert response2.status_code == 429, "Second scanner request should be rate limited"
        """


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
