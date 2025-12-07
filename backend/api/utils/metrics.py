"""
Prometheus-style metrics for monitoring Wave B scoring functionality.

Provides simple counters for tracking scored events and rescore errors.
"""

from typing import Dict
from datetime import datetime

# Simple in-memory counters (reset on restart)
_METRICS: Dict[str, int] = {
    "scored_events_total": 0,
    "rescore_errors_total": 0,
    "rescore_requests_total": 0,
    "scores_rescore_rate_limited_total": 0,  # Rescore requests blocked by rate limit
    "score_cache_hits_total": 0,
    "score_cache_misses_total": 0,
    "scores_denied_free_total": 0,  # Wave B: Free users denied access
    "scores_served_total": 0,  # Wave B: Pro/Team users served
    "alerts_evaluated_total": 0,  # Wave C: Total alerts evaluated
    "alerts_deduped_total": 0,  # Wave C: Alerts blocked by deduplication
    "alerts_rate_limited_total": 0,  # Wave C: Alerts blocked by rate limiting
    "portfolio_positions_total": 0,  # Wave D: Total portfolio positions stored
    "portfolio_insights_requests_total": 0,  # Wave D: Total insights requests
    "ws_connections": 0,  # Wave E: Current WebSocket connections (gauge)
    "ws_disconnects_total": 0,  # Wave E: Total WebSocket disconnects
    "api_calls_monthly_free": 0,  # Wave F: Monthly API calls by free users
    "api_calls_monthly_pro": 0,  # Wave F: Monthly API calls by pro users
    "api_calls_monthly_team": 0,  # Wave F: Monthly API calls by team users
    "alerts_sent_monthly_free": 0,  # Wave F: Monthly alerts sent to free users
    "alerts_sent_monthly_pro": 0,  # Wave F: Monthly alerts sent to pro users
    "alerts_sent_monthly_team": 0,  # Wave F: Monthly alerts sent to team users
    "ai_requests_total": 0,  # AI: Total AI requests
    "ai_requests_error_total": 0,  # AI: Failed AI requests
    "ai_requests_blocked_quota_total": 0,  # AI: Requests blocked by quota
    "ai_slow_requests_total": 0,  # AI: Requests taking >5s
}

# Histogram buckets for AI request latency (in seconds)
_AI_LATENCY_BUCKETS = [0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
_AI_LATENCY_HISTOGRAM: Dict[str, Dict[str, int]] = {}  # endpoint -> bucket -> count

# Manual scan job metrics (with labels support)
_LABELED_METRICS: Dict[str, Dict[str, int]] = {
    "manual_scan_jobs_total": {},  # scope=company|scanner
    "manual_scan_jobs_error_total": {},  # scope=company|scanner
    "alerts_sent_total": {},  # channel=in_app|email
    "ws_messages_sent_total": {},  # type=event.new|event.scored|heartbeat
}

_START_TIME = datetime.utcnow()
_CACHE_SIZE_GETTER = None  # Function to get cache size (set by scores module)


def increment_metric(metric_name: str, value: int = 1):
    """Increment a metric counter."""
    if metric_name in _METRICS:
        _METRICS[metric_name] += value


def increment_counter(metric_name: str, labels: Dict[str, str] = None, value: int = 1):
    """
    Increment a counter with optional labels.
    
    Args:
        metric_name: Name of the metric to increment
        labels: Optional dictionary of label key-value pairs
        value: Amount to increment by (default 1)
    """
    if metric_name in _METRICS:
        _METRICS[metric_name] += value
    elif metric_name in _LABELED_METRICS:
        if labels:
            label_key = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            if label_key not in _LABELED_METRICS[metric_name]:
                _LABELED_METRICS[metric_name][label_key] = 0
            _LABELED_METRICS[metric_name][label_key] += value


def get_metrics() -> Dict[str, int]:
    """Get current metric values."""
    return _METRICS.copy()


def observe_ai_latency(endpoint: str, latency_seconds: float) -> None:
    """
    Observe AI request latency for histogram tracking.
    
    Args:
        endpoint: AI endpoint (e.g., "analyze", "chat")
        latency_seconds: Request latency in seconds
    """
    global _AI_LATENCY_HISTOGRAM
    
    if endpoint not in _AI_LATENCY_HISTOGRAM:
        _AI_LATENCY_HISTOGRAM[endpoint] = {f"le_{b}": 0 for b in _AI_LATENCY_BUCKETS}
        _AI_LATENCY_HISTOGRAM[endpoint]["le_inf"] = 0
        _AI_LATENCY_HISTOGRAM[endpoint]["sum"] = 0
        _AI_LATENCY_HISTOGRAM[endpoint]["count"] = 0
    
    hist = _AI_LATENCY_HISTOGRAM[endpoint]
    hist["sum"] += latency_seconds
    hist["count"] += 1
    
    for bucket in _AI_LATENCY_BUCKETS:
        if latency_seconds <= bucket:
            hist[f"le_{bucket}"] += 1
    hist["le_inf"] += 1


def set_cache_size_getter(getter_func):
    """Set function to get current cache size."""
    global _CACHE_SIZE_GETTER
    _CACHE_SIZE_GETTER = getter_func


def get_metrics_text() -> str:
    """
    Get metrics in Prometheus text format.
    
    Returns:
        str: Prometheus-formatted metrics
    """
    uptime_seconds = int((datetime.utcnow() - _START_TIME).total_seconds())
    cache_size = _CACHE_SIZE_GETTER() if _CACHE_SIZE_GETTER else 0
    
    lines = [
        "# HELP scored_events_total Total number of events scored",
        "# TYPE scored_events_total counter",
        f"scored_events_total {_METRICS['scored_events_total']}",
        "",
        "# HELP rescore_errors_total Total number of rescore errors",
        "# TYPE rescore_errors_total counter",
        f"rescore_errors_total {_METRICS['rescore_errors_total']}",
        "",
        "# HELP rescore_requests_total Total number of rescore requests",
        "# TYPE rescore_requests_total counter",
        f"rescore_requests_total {_METRICS['rescore_requests_total']}",
        "",
        "# HELP scores_rescore_rate_limited_total Total number of rescore requests blocked by rate limit",
        "# TYPE scores_rescore_rate_limited_total counter",
        f"scores_rescore_rate_limited_total {_METRICS['scores_rescore_rate_limited_total']}",
        "",
        "# HELP score_cache_hits_total Total number of score cache hits",
        "# TYPE score_cache_hits_total counter",
        f"score_cache_hits_total {_METRICS['score_cache_hits_total']}",
        "",
        "# HELP score_cache_misses_total Total number of score cache misses",
        "# TYPE score_cache_misses_total counter",
        f"score_cache_misses_total {_METRICS['score_cache_misses_total']}",
        "",
        "# HELP scores_denied_free_total Total number of scores denied to free users",
        "# TYPE scores_denied_free_total counter",
        f"scores_denied_free_total {_METRICS['scores_denied_free_total']}",
        "",
        "# HELP scores_served_total Total number of scores served to Pro/Team users",
        "# TYPE scores_served_total counter",
        f"scores_served_total {_METRICS['scores_served_total']}",
        "",
        "# HELP scores_cache_size Current number of items in score cache",
        "# TYPE scores_cache_size gauge",
        f"scores_cache_size {cache_size}",
        "",
        "# HELP manual_scan_jobs_total Total number of successful manual scan jobs",
        "# TYPE manual_scan_jobs_total counter",
    ]
    
    # Add labeled metrics for manual scan jobs
    if _LABELED_METRICS["manual_scan_jobs_total"]:
        for label_str, count in _LABELED_METRICS["manual_scan_jobs_total"].items():
            lines.append(f"manual_scan_jobs_total{{{label_str}}} {count}")
    else:
        lines.append("manual_scan_jobs_total 0")
    
    lines.extend([
        "",
        "# HELP manual_scan_jobs_error_total Total number of failed manual scan jobs",
        "# TYPE manual_scan_jobs_error_total counter",
    ])
    
    if _LABELED_METRICS["manual_scan_jobs_error_total"]:
        for label_str, count in _LABELED_METRICS["manual_scan_jobs_error_total"].items():
            lines.append(f"manual_scan_jobs_error_total{{{label_str}}} {count}")
    else:
        lines.append("manual_scan_jobs_error_total 0")
    
    lines.extend([
        "",
        "# HELP alerts_evaluated_total Total number of alerts evaluated",
        "# TYPE alerts_evaluated_total counter",
        f"alerts_evaluated_total {_METRICS['alerts_evaluated_total']}",
        "",
        "# HELP alerts_deduped_total Total number of alerts blocked by deduplication",
        "# TYPE alerts_deduped_total counter",
        f"alerts_deduped_total {_METRICS['alerts_deduped_total']}",
        "",
        "# HELP alerts_rate_limited_total Total number of alerts blocked by rate limiting",
        "# TYPE alerts_rate_limited_total counter",
        f"alerts_rate_limited_total {_METRICS['alerts_rate_limited_total']}",
        "",
        "# HELP alerts_sent_total Total number of alerts sent by channel",
        "# TYPE alerts_sent_total counter",
    ])
    
    if _LABELED_METRICS["alerts_sent_total"]:
        for label_str, count in _LABELED_METRICS["alerts_sent_total"].items():
            lines.append(f"alerts_sent_total{{{label_str}}} {count}")
    else:
        lines.append("alerts_sent_total 0")
    
    lines.extend([
        "",
        "# HELP portfolio_positions_total Total number of portfolio positions stored",
        "# TYPE portfolio_positions_total counter",
        f"portfolio_positions_total {_METRICS['portfolio_positions_total']}",
        "",
        "# HELP portfolio_insights_requests_total Total number of portfolio insights requests",
        "# TYPE portfolio_insights_requests_total counter",
        f"portfolio_insights_requests_total {_METRICS['portfolio_insights_requests_total']}",
        "",
        "# HELP ws_connections Current number of WebSocket connections",
        "# TYPE ws_connections gauge",
        f"ws_connections {_METRICS['ws_connections']}",
        "",
        "# HELP ws_disconnects_total Total number of WebSocket disconnects",
        "# TYPE ws_disconnects_total counter",
        f"ws_disconnects_total {_METRICS['ws_disconnects_total']}",
        "",
        "# HELP ws_messages_sent_total Total number of WebSocket messages sent by type",
        "# TYPE ws_messages_sent_total counter",
    ])
    
    if _LABELED_METRICS["ws_messages_sent_total"]:
        for label_str, count in _LABELED_METRICS["ws_messages_sent_total"].items():
            lines.append(f"ws_messages_sent_total{{{label_str}}} {count}")
    else:
        lines.append("ws_messages_sent_total 0")
    
    lines.extend([
        "",
        "# HELP api_calls_monthly Monthly API calls by plan",
        "# TYPE api_calls_monthly counter",
        f"api_calls_monthly{{plan=\"free\"}} {_METRICS['api_calls_monthly_free']}",
        f"api_calls_monthly{{plan=\"pro\"}} {_METRICS['api_calls_monthly_pro']}",
        f"api_calls_monthly{{plan=\"team\"}} {_METRICS['api_calls_monthly_team']}",
        "",
        "# HELP alerts_sent_monthly Monthly alerts sent by plan",
        "# TYPE alerts_sent_monthly counter",
        f"alerts_sent_monthly{{plan=\"free\"}} {_METRICS['alerts_sent_monthly_free']}",
        f"alerts_sent_monthly{{plan=\"pro\"}} {_METRICS['alerts_sent_monthly_pro']}",
        f"alerts_sent_monthly{{plan=\"team\"}} {_METRICS['alerts_sent_monthly_team']}",
        "",
        "# HELP ai_requests_total Total AI requests",
        "# TYPE ai_requests_total counter",
        f"ai_requests_total {_METRICS['ai_requests_total']}",
        "",
        "# HELP ai_requests_error_total Failed AI requests",
        "# TYPE ai_requests_error_total counter",
        f"ai_requests_error_total {_METRICS['ai_requests_error_total']}",
        "",
        "# HELP ai_requests_blocked_quota_total AI requests blocked by quota",
        "# TYPE ai_requests_blocked_quota_total counter",
        f"ai_requests_blocked_quota_total {_METRICS['ai_requests_blocked_quota_total']}",
        "",
        "# HELP ai_slow_requests_total AI requests taking >5s",
        "# TYPE ai_slow_requests_total counter",
        f"ai_slow_requests_total {_METRICS['ai_slow_requests_total']}",
        "",
        "# HELP ai_request_latency_seconds AI request latency distribution",
        "# TYPE ai_request_latency_seconds histogram",
    ])
    
    for endpoint, hist in _AI_LATENCY_HISTOGRAM.items():
        for bucket in _AI_LATENCY_BUCKETS:
            lines.append(f'ai_request_latency_seconds_bucket{{endpoint="{endpoint}",le="{bucket}"}} {hist.get(f"le_{bucket}", 0)}')
        lines.append(f'ai_request_latency_seconds_bucket{{endpoint="{endpoint}",le="+Inf"}} {hist.get("le_inf", 0)}')
        lines.append(f'ai_request_latency_seconds_sum{{endpoint="{endpoint}"}} {hist.get("sum", 0):.3f}')
        lines.append(f'ai_request_latency_seconds_count{{endpoint="{endpoint}"}} {hist.get("count", 0)}')
    
    lines.extend([
        "",
        "# HELP api_uptime_seconds API uptime in seconds",
        "# TYPE api_uptime_seconds gauge",
        f"api_uptime_seconds {uptime_seconds}",
        "",
    ])
    
    return "\n".join(lines)
