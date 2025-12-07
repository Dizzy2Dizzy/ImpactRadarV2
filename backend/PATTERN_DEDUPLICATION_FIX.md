# Pattern Detection Deduplication Fix

## Problem
The pattern detector was checking for duplicates globally per `pattern_id + ticker + date`, which caused:
- System alerts (created by background jobs with `user_id=NULL`) blocked user-specific alerts
- Users couldn't get their own alerts for patterns that had already triggered system-wide

## Solution
Updated `pattern_detector.py` to scope deduplication by user context:

### Key Changes

1. **Determine target_user_id based on context:**
   ```python
   if pattern.created_by is not None:
       # User-owned pattern: use pattern owner
       target_user_id = pattern.created_by
   else:
       # System pattern: use context
       target_user_id = user_id  # None for background jobs, user_id for API calls
   ```

2. **Updated duplicate check to include user_id:**
   ```python
   existing_alert = db.query(PatternAlert).filter(
       and_(
           PatternAlert.pattern_id == pattern.id,
           PatternAlert.ticker == check_ticker,
           PatternAlert.user_id == target_user_id,  # NEW: scope by user
           PatternAlert.detected_at >= today_start
       )
   ).first()
   ```

3. **Updated alert creation to use target_user_id:**
   - System patterns in background jobs → `user_id=NULL`
   - System patterns for specific user → `user_id={user_id}`
   - User patterns → `user_id={pattern.created_by}`

## Behavior After Fix

### Background Job (No user_id)
- Creates system alerts with `user_id=NULL`
- Only prevents duplicate system alerts for same pattern+ticker on same day
- Does NOT block user-specific alerts

### API Call (With user_id)
- For system patterns: Creates user-specific alert with `user_id={user_id}`
- For user patterns: Creates alert with `user_id={pattern.created_by}`
- Only prevents duplicate alerts for that specific user

### Parallel Alerts Allowed
Both can exist simultaneously:
- System alert: `(pattern_id=1, ticker=AAPL, user_id=NULL, date=2025-11-21)`
- User alert: `(pattern_id=1, ticker=AAPL, user_id=305, date=2025-11-21)`

## Testing

### Test Case 1: Background Job
```python
# Background job creates system alert
alerts = detect_patterns(db=session)  # user_id=None
# Result: Alert created with user_id=NULL
```

### Test Case 2: User API Call
```python
# User 305 requests detection
alerts = detect_patterns(db=session, user_id=305)
# Result: Alert created with user_id=305 (even if system alert exists)
```

### Test Case 3: Deduplication
```python
# First call
alerts = detect_patterns(db=session, user_id=305, ticker="AAPL", pattern_id=1)
# Result: Alert created

# Second call (same day)
alerts = detect_patterns(db=session, user_id=305, ticker="AAPL", pattern_id=1)
# Result: No alert created (duplicate for this user)
```

## Files Modified
- `backend/releaseradar/services/pattern_detector.py`

## Backward Compatibility
✅ No breaking changes - function signature unchanged
✅ Existing callers work without modification:
- `backend/api/routers/patterns.py` (API endpoint)
- `backend/jobs/detect_patterns.py` (background job)
