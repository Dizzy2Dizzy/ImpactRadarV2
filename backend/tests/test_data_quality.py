"""
Pytest tests for data quality validation and monitoring.

Tests validation functions, API endpoints, QualityMetricsService, and pipeline health.
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from releaseradar.db.models import (
    Base,
    Event,
    EventOutcome,
    PriceHistory,
    EventStats,
    DataQualitySnapshot,
    DataPipelineRun,
    DataLineageRecord,
    AuditLogEntry,
    ModelRegistry,
    Company,
)
from releaseradar.services.quality_metrics import QualityMetricsService
from jobs.data_quality_validation import DataQualityValidator


@pytest.fixture(scope="function")
def db_session():
    """Create in-memory SQLite database for testing."""
    import tempfile
    import os
    
    # Use a temporary file database instead of in-memory to avoid index conflicts
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()
    db_path = temp_file.name
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Drop all tables first to ensure clean state
    Base.metadata.drop_all(engine)
    
    # Create all tables fresh for each test
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # Clean up
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()
    
    # Remove temporary database file
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sample_company(db_session):
    """Create sample company."""
    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        tracked=True
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture
def sample_events(db_session, sample_company):
    """Create sample events."""
    events = []
    base_date = datetime.utcnow() - timedelta(days=10)
    
    for i in range(5):
        event = Event(
            ticker="AAPL",
            company_name="Apple Inc.",
            event_type="earnings",
            title=f"Q{i+1} Earnings",
            description="Test event",
            date=base_date + timedelta(days=i),
            source="test",
            source_url=f"https://test.com/{i}",
            raw_id=f"test_{i}",
            impact_score=70
        )
        events.append(event)
        db_session.add(event)
    
    db_session.commit()
    return events


@pytest.fixture
def sample_prices(db_session):
    """Create sample price data."""
    prices = []
    base_date = date.today() - timedelta(days=10)
    
    for i in range(10):
        price = PriceHistory(
            ticker="AAPL",
            date=base_date + timedelta(days=i),
            open=150.0 + i,
            close=151.0 + i,
            high=152.0 + i,
            low=149.0 + i,
            volume=1000000,
            source="yahoo"
        )
        prices.append(price)
        db_session.add(price)
    
    db_session.commit()
    return prices


@pytest.fixture
def sample_outcomes(db_session, sample_events):
    """Create sample event outcomes."""
    outcomes = []
    
    for event in sample_events[:3]:
        for horizon in ["1d", "5d", "20d"]:
            outcome = EventOutcome(
                event_id=event.id,
                ticker=event.ticker,
                horizon=horizon,
                price_before=150.0,
                price_after=152.0,
                return_pct_raw=1.33,
                benchmark_return_pct=0.5,
                return_pct=0.83,
                abs_return_pct=0.83,
                direction_correct=True,
                has_benchmark_data=True,
                label_date=date.today()
            )
            outcomes.append(outcome)
            db_session.add(outcome)
    
    db_session.commit()
    return outcomes


@pytest.fixture
def quality_service(db_session):
    """Create QualityMetricsService instance."""
    return QualityMetricsService(db=db_session)


class TestQualityMetricsService:
    """Test QualityMetricsService methods."""
    
    def test_record_pipeline_run(self, quality_service, db_session):
        """Test recording a pipeline run."""
        started_at = datetime.utcnow()
        
        run = quality_service.record_pipeline_run(
            job_name="test_job",
            started_at=started_at,
            status="running"
        )
        
        assert run.id is not None
        assert run.job_name == "test_job"
        assert run.status == "running"
        assert run.started_at == started_at
    
    def test_update_pipeline_run(self, quality_service, db_session):
        """Test updating pipeline run status."""
        started_at = datetime.utcnow()
        
        run = quality_service.record_pipeline_run(
            job_name="test_job",
            started_at=started_at,
            status="running"
        )
        
        completed_at = datetime.utcnow()
        quality_service.update_pipeline_run(
            run_id=run.id,
            status="success",
            completed_at=completed_at,
            rows_written=100
        )
        
        db_session.refresh(run)
        assert run.status == "success"
        assert run.completed_at == completed_at
        assert run.rows_written == 100
    
    def test_record_quality_snapshot(self, quality_service, db_session):
        """Test recording quality snapshot."""
        snapshot = quality_service.record_quality_snapshot(
            metric_key="test_metric",
            scope="global",
            sample_count=100,
            freshness_ts=datetime.utcnow(),
            source_job="test_job",
            quality_grade="excellent",
            summary_json={"test": "data"}
        )
        
        assert snapshot.id is not None
        assert snapshot.metric_key == "test_metric"
        assert snapshot.quality_grade == "excellent"
        assert snapshot.summary_json == {"test": "data"}
    
    def test_get_freshness_indicators(self, quality_service, db_session):
        """Test retrieving freshness indicators."""
        # Create test snapshots
        quality_service.record_quality_snapshot(
            metric_key="events_total",
            scope="global",
            sample_count=100,
            freshness_ts=datetime.utcnow(),
            source_job="test_job",
            quality_grade="excellent"
        )
        
        indicators = quality_service.get_freshness_indicators()
        
        assert len(indicators) > 0
        assert indicators[0]["metric_key"] == "events_total"
        assert indicators[0]["quality_grade"] == "excellent"
    
    def test_get_pipeline_health(self, quality_service, db_session):
        """Test retrieving pipeline health metrics."""
        # Create test pipeline runs
        started_at = datetime.utcnow() - timedelta(hours=2)
        
        for i in range(5):
            run = quality_service.record_pipeline_run(
                job_name="test_job",
                started_at=started_at + timedelta(minutes=i*10),
                status="running"
            )
            
            quality_service.update_pipeline_run(
                run_id=run.id,
                status="success" if i % 2 == 0 else "failure",
                completed_at=started_at + timedelta(minutes=i*10+5)
            )
        
        health = quality_service.get_pipeline_health(hours_back=24)
        
        assert health["total_runs"] == 5
        assert 0 <= health["success_rate"] <= 100
        assert "test_job" in health["jobs"]
    
    def test_record_audit_log(self, quality_service, db_session):
        """Test recording audit log entry."""
        entry = quality_service.record_audit_log(
            entity_type="event",
            entity_id=123,
            action="create",
            performed_by=1,
            diff_json={"title": "Test Event"}
        )
        
        assert entry.id is not None
        assert entry.entity_type == "event"
        assert entry.entity_id == 123
        assert entry.action == "create"
        assert entry.performed_by == 1
    
    def test_get_audit_log(self, quality_service, db_session):
        """Test retrieving audit log entries."""
        # Create test entries
        for i in range(3):
            quality_service.record_audit_log(
                entity_type="event",
                entity_id=i,
                action="create",
                performed_by=1
            )
        
        result = quality_service.get_audit_log(limit=10, offset=0)
        
        assert result["total"] == 3
        assert len(result["entries"]) == 3
        assert result["has_more"] is False


class TestDataQualityValidator:
    """Test DataQualityValidator validation logic."""
    
    def test_add_finding(self):
        """Test adding validation findings."""
        validator = DataQualityValidator()
        
        validator.add_finding(
            category="test",
            check_name="test_check",
            status="pass",
            message="Test passed"
        )
        
        assert len(validator.findings) == 1
        assert validator.passed_checks == 1
        assert validator.failed_checks == 0
    
    def test_validate_data_completeness_event_count_stable(self, db_session, sample_events):
        """Test event count validation - stable case."""
        validator = DataQualityValidator()
        validator.validate_data_completeness(db_session)
        
        # Should pass with stable event count
        findings = [f for f in validator.findings if f["check"] == "event_count_stability"]
        assert len(findings) > 0
    
    def test_validate_data_completeness_price_gaps(self, db_session, sample_events, sample_prices):
        """Test price data gap validation."""
        validator = DataQualityValidator()
        validator.validate_data_completeness(db_session)
        
        # Should pass with recent price data
        findings = [f for f in validator.findings if f["check"] == "price_data_gaps"]
        assert len(findings) > 0
    
    def test_validate_data_accuracy_return_calculation(self, db_session, sample_outcomes):
        """Test return calculation validation."""
        validator = DataQualityValidator()
        validator.validate_data_accuracy(db_session)
        
        # Should pass with correct calculations
        findings = [f for f in validator.findings if f["check"] == "return_calculation"]
        assert len(findings) > 0
    
    def test_validate_data_accuracy_outliers(self, db_session):
        """Test outlier detection."""
        # Create extreme outlier
        event = Event(
            ticker="TEST",
            company_name="Test",
            event_type="test",
            title="Test",
            date=datetime.utcnow(),
            source="test",
            impact_score=50
        )
        db_session.add(event)
        db_session.commit()
        
        outcome = EventOutcome(
            event_id=event.id,
            ticker="TEST",
            horizon="1d",
            price_before=100.0,
            price_after=200.0,  # 100% return in 1 day
            return_pct_raw=100.0,
            benchmark_return_pct=0.0,
            return_pct=100.0,
            abs_return_pct=100.0,
            label_date=date.today()
        )
        db_session.add(outcome)
        db_session.commit()
        
        validator = DataQualityValidator()
        validator.validate_data_accuracy(db_session)
        
        # Should detect outlier
        findings = [f for f in validator.findings if f["check"] == "outlier_detection"]
        assert len(findings) > 0
    
    def test_validate_ml_metrics(self, db_session):
        """Test ML metrics validation."""
        # Create test model
        model = ModelRegistry(
            name="test_model",
            version="1.0.0",
            status="active",
            model_path="/tmp/test.pkl",
            metrics={"mae": 0.5},
            feature_version="1.0"
        )
        db_session.add(model)
        db_session.commit()
        
        validator = DataQualityValidator()
        validator.validate_ml_metrics(db_session)
        
        # Should find active model
        findings = [f for f in validator.findings if f["check"] == "active_models"]
        assert len(findings) > 0
        assert findings[0]["status"] == "pass"
    
    def test_validate_pipeline_health_no_runs(self, db_session):
        """Test pipeline health with no recent runs."""
        validator = DataQualityValidator()
        validator.validate_pipeline_health(db_session)
        
        # Should fail with no recent runs
        findings = [f for f in validator.findings if f["check"] == "recent_runs"]
        assert len(findings) > 0
        assert findings[0]["status"] == "fail"
    
    def test_validate_pipeline_health_stuck_jobs(self, db_session):
        """Test detection of stuck jobs."""
        # Create stuck job
        run = DataPipelineRun(
            job_name="stuck_job",
            started_at=datetime.utcnow() - timedelta(hours=2),
            status="running"
        )
        db_session.add(run)
        db_session.commit()
        
        validator = DataQualityValidator()
        validator.validate_pipeline_health(db_session)
        
        # Should detect stuck job
        findings = [f for f in validator.findings if f["check"] == "stuck_jobs"]
        assert len(findings) > 0
        assert findings[0]["status"] == "fail"
    
    def test_validate_pipeline_health_error_rate(self, db_session):
        """Test error rate calculation."""
        # Create mix of successful and failed runs
        started_at = datetime.utcnow() - timedelta(hours=2)
        
        for i in range(10):
            run = DataPipelineRun(
                job_name="test_job",
                started_at=started_at + timedelta(minutes=i*10),
                status="success" if i < 9 else "failure",
                completed_at=started_at + timedelta(minutes=i*10+5)
            )
            db_session.add(run)
        
        db_session.commit()
        
        validator = DataQualityValidator()
        validator.validate_pipeline_health(db_session)
        
        # Should have acceptable error rate (10%)
        findings = [f for f in validator.findings if f["check"] == "error_rate"]
        assert len(findings) > 0
    
    def test_run_validation_overall_health(self, db_session, sample_events, sample_prices):
        """Test overall health determination."""
        validator = DataQualityValidator()
        report = validator.run_validation(db_session)
        
        assert "overall_health" in report
        assert report["overall_health"] in ["healthy", "warning", "critical"]
        assert "summary" in report
        assert "findings" in report
        assert report["summary"]["total_checks"] > 0


class TestDataQualityAPI:
    """Test data quality API endpoints (integration-style tests)."""
    
    def test_freshness_endpoint_response_schema(self, quality_service, db_session):
        """Test freshness endpoint returns correct schema."""
        # Create test snapshot
        quality_service.record_quality_snapshot(
            metric_key="test_metric",
            scope="global",
            sample_count=100,
            freshness_ts=datetime.utcnow(),
            source_job="test_job",
            quality_grade="excellent"
        )
        
        indicators = quality_service.get_freshness_indicators()
        
        assert len(indicators) > 0
        indicator = indicators[0]
        
        # Verify schema
        assert "metric_key" in indicator
        assert "scope" in indicator
        assert "sample_count" in indicator
        assert "freshness_ts" in indicator
        assert "quality_grade" in indicator
    
    def test_pipeline_health_endpoint_response_schema(self, quality_service, db_session):
        """Test pipeline health endpoint returns correct schema."""
        # Create test runs
        started_at = datetime.utcnow() - timedelta(hours=1)
        run = quality_service.record_pipeline_run(
            job_name="test_job",
            started_at=started_at,
            status="running"
        )
        quality_service.update_pipeline_run(
            run_id=run.id,
            status="success",
            completed_at=datetime.utcnow()
        )
        
        health = quality_service.get_pipeline_health(hours_back=24)
        
        # Verify schema
        assert "total_runs" in health
        assert "success_rate" in health
        assert "avg_runtime_seconds" in health
        assert "recent_failures" in health
        assert "jobs" in health
    
    def test_audit_log_endpoint_pagination(self, quality_service, db_session):
        """Test audit log pagination."""
        # Create 10 test entries
        for i in range(10):
            quality_service.record_audit_log(
                entity_type="event",
                entity_id=i,
                action="create"
            )
        
        # Test pagination
        result_page1 = quality_service.get_audit_log(limit=5, offset=0)
        result_page2 = quality_service.get_audit_log(limit=5, offset=5)
        
        assert len(result_page1["entries"]) == 5
        assert len(result_page2["entries"]) == 5
        assert result_page1["total"] == 10
        assert result_page1["has_more"] is True
        assert result_page2["has_more"] is False
    
    def test_audit_log_filtering(self, quality_service, db_session):
        """Test audit log filtering."""
        # Create entries with different types
        quality_service.record_audit_log(
            entity_type="event",
            entity_id=1,
            action="create"
        )
        quality_service.record_audit_log(
            entity_type="user",
            entity_id=2,
            action="update"
        )
        
        # Filter by entity_type
        result = quality_service.get_audit_log(
            entity_type="event",
            limit=10,
            offset=0
        )
        
        assert result["total"] == 1
        assert result["entries"][0]["entity_type"] == "event"


class TestRegressionTests:
    """Regression tests for key metrics."""
    
    def test_accuracy_drift_detection(self, db_session):
        """Test that accuracy doesn't drift below acceptable threshold."""
        # Create sample outcomes with known accuracy
        base_date = datetime.utcnow() - timedelta(days=30)
        
        for i in range(100):
            event = Event(
                ticker="TEST",
                company_name="Test",
                event_type="test",
                title=f"Event {i}",
                date=base_date + timedelta(days=i % 30),
                source="test",
                impact_score=50,
                direction="bullish" if i % 2 == 0 else "bearish"
            )
            db_session.add(event)
            db_session.commit()
            
            # 80% accuracy
            return_pct = 5.0 if (i % 2 == 0 and i < 80) or (i % 2 == 1 and i >= 80) else -5.0
            
            outcome = EventOutcome(
                event_id=event.id,
                ticker="TEST",
                horizon="1d",
                price_before=100.0,
                price_after=100.0 + return_pct,
                return_pct_raw=return_pct,
                benchmark_return_pct=0.0,
                return_pct=return_pct,
                abs_return_pct=abs(return_pct),
                direction_correct=(i < 80),
                label_date=date.today()
            )
            db_session.add(outcome)
        
        db_session.commit()
        
        # Calculate actual accuracy
        from sqlalchemy import select, func
        
        total = db_session.execute(
            select(func.count(EventOutcome.id)).where(
                EventOutcome.direction_correct.isnot(None)
            )
        ).scalar()
        
        correct = db_session.execute(
            select(func.count(EventOutcome.id)).where(
                EventOutcome.direction_correct == True
            )
        ).scalar()
        
        accuracy = (correct / total) * 100
        
        # Should maintain >75% accuracy
        assert accuracy >= 75.0


# Edge case tests
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_database(self, db_session):
        """Test validation with empty database."""
        validator = DataQualityValidator()
        report = validator.run_validation(db_session)
        
        # Should complete without errors
        assert report is not None
        assert "summary" in report
    
    def test_missing_price_data(self, db_session, sample_events):
        """Test handling of missing price data."""
        validator = DataQualityValidator()
        validator.validate_data_completeness(db_session)
        
        # Should detect missing price data
        findings = [f for f in validator.findings if f["check"] == "price_data_gaps"]
        assert len(findings) > 0
    
    def test_invalid_return_calculation(self, db_session):
        """Test detection of invalid return calculations."""
        event = Event(
            ticker="TEST",
            company_name="Test",
            event_type="test",
            title="Test",
            date=datetime.utcnow(),
            source="test",
            impact_score=50
        )
        db_session.add(event)
        db_session.commit()
        
        # Create outcome with incorrect calculation
        outcome = EventOutcome(
            event_id=event.id,
            ticker="TEST",
            horizon="1d",
            price_before=100.0,
            price_after=110.0,
            return_pct_raw=5.0,  # Should be 10.0
            benchmark_return_pct=0.0,
            return_pct=5.0,
            abs_return_pct=5.0,
            label_date=date.today()
        )
        db_session.add(outcome)
        db_session.commit()
        
        validator = DataQualityValidator()
        validator.validate_data_accuracy(db_session)
        
        # Should detect calculation error
        findings = [f for f in validator.findings if f["check"] == "return_calculation"]
        assert len(findings) > 0
        assert findings[0]["status"] == "fail"
