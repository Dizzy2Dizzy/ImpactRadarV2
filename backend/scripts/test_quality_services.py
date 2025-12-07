"""
Test Data Quality Service Methods

Verifies that QualityMetricsService methods return non-empty data.

Usage:
    cd backend
    python3 scripts/test_quality_services.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from releaseradar.db.session import get_db_context
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.log_config import logger


def test_freshness_indicators():
    """Test get_freshness_indicators method."""
    logger.info("=== Testing get_freshness_indicators() ===")
    
    with get_db_context() as db:
        service = QualityMetricsService(db)
        indicators = service.get_freshness_indicators()
        
        logger.info(f"Returned {len(indicators)} freshness indicators")
        
        if len(indicators) == 0:
            logger.error("✗ FAIL: No indicators returned!")
            return False
        
        for ind in indicators[:3]:
            logger.info(f"  - {ind['metric_key']}: {ind['quality_grade']} (samples={ind['sample_count']})")
        
        logger.info("✓ PASS: Freshness indicators returned successfully")
        return True


def test_pipeline_health():
    """Test get_pipeline_health method."""
    logger.info("=== Testing get_pipeline_health() ===")
    
    with get_db_context() as db:
        service = QualityMetricsService(db)
        health = service.get_pipeline_health(hours_back=24)
        
        logger.info(f"Total runs: {health['total_runs']}")
        logger.info(f"Success rate: {health['success_rate']}%")
        logger.info(f"Avg runtime: {health['avg_runtime_seconds']}s")
        logger.info(f"Recent failures: {len(health['recent_failures'])}")
        logger.info(f"Jobs tracked: {len(health['jobs'])}")
        
        if health['total_runs'] == 0:
            logger.error("✗ FAIL: No pipeline runs found!")
            return False
        
        for job_name, stats in list(health['jobs'].items())[:3]:
            logger.info(f"  - {job_name}: {stats['total']} runs ({stats.get('success', 0)} success, {stats.get('failure', 0)} failed)")
        
        logger.info("✓ PASS: Pipeline health returned successfully")
        return True


def test_audit_log():
    """Test get_audit_log method."""
    logger.info("=== Testing get_audit_log() ===")
    
    with get_db_context() as db:
        service = QualityMetricsService(db)
        result = service.get_audit_log(limit=10)
        
        logger.info(f"Total entries: {result['total']}")
        logger.info(f"Returned: {len(result['entries'])} entries")
        logger.info(f"Has more: {result['has_more']}")
        
        if result['total'] == 0:
            logger.error("✗ FAIL: No audit log entries found!")
            return False
        
        for entry in result['entries'][:3]:
            logger.info(f"  - {entry['action']} {entry['entity_type']}#{entry['entity_id']} by {entry.get('performed_by') or 'system'}")
        
        logger.info("✓ PASS: Audit log returned successfully")
        return True


def test_metric_lineage():
    """Test get_metric_lineage method."""
    logger.info("=== Testing get_metric_lineage() ===")
    
    with get_db_context() as db:
        service = QualityMetricsService(db)
        records = service.get_metric_lineage(metric_key="event_created", limit=10)
        
        logger.info(f"Returned {len(records)} lineage records for 'event_created'")
        
        if len(records) == 0:
            logger.warning("⚠ WARNING: No lineage records found for 'event_created'")
            logger.info("  Trying 'outcome_labeled' instead...")
            records = service.get_metric_lineage(metric_key="outcome_labeled", limit=10)
            logger.info(f"  Returned {len(records)} lineage records for 'outcome_labeled'")
        
        if len(records) > 0:
            for rec in records[:3]:
                logger.info(f"  - {rec['entity_type']}#{rec['entity_id']} from {rec.get('source_url', 'N/A')[:50]}...")
            logger.info("✓ PASS: Lineage records returned successfully")
            return True
        else:
            logger.error("✗ FAIL: No lineage records found!")
            return False


def main():
    """Main test execution."""
    logger.info("=" * 60)
    logger.info("TESTING DATA QUALITY SERVICE METHODS")
    logger.info("=" * 60)
    
    results = {
        "freshness_indicators": test_freshness_indicators(),
        "pipeline_health": test_pipeline_health(),
        "audit_log": test_audit_log(),
        "metric_lineage": test_metric_lineage(),
    }
    
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    logger.info("=" * 60)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    if passed == total:
        logger.info("✓ SUCCESS: All service methods working correctly!")
        return 0
    else:
        logger.error(f"✗ FAILURE: {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
