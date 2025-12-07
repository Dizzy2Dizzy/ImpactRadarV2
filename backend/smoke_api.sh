#!/usr/bin/env bash
set -euo pipefail

# API Smoke Test Script
# Tests API key authentication and endpoint gating

echo "=== Release Radar API Smoke Tests ==="
echo ""

# Configuration
BASE_URL="${BASE_URL:-http://localhost:8080}"
API_KEY="${RR_TEST_KEY:-missing}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASS=0
FAIL=0

# Helper functions
test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASS++))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAIL++))
}

test_warn() {
    echo -e "${YELLOW}!${NC} $1"
}

# Test 1: Public endpoint (no auth required)
echo "Test 1: Public endpoint (no auth required)"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/events/public")
if [ "$HTTP_CODE" -eq 200 ]; then
    test_pass "Public endpoint accessible without API key (200)"
else
    test_fail "Public endpoint returned ${HTTP_CODE} instead of 200"
fi
echo ""

# Test 2: Protected endpoint without API key
echo "Test 2: Protected endpoint without API key"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/events/search?limit=3")
if [ "$HTTP_CODE" -eq 401 ]; then
    test_pass "Protected endpoint requires API key (401)"
else
    test_fail "Protected endpoint returned ${HTTP_CODE} instead of 401"
fi
echo ""

# Test 3: Health check
echo "Test 3: Health check endpoint"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/healthz")
if [ "$HTTP_CODE" -eq 200 ]; then
    test_pass "Health check endpoint accessible (200)"
else
    test_fail "Health check endpoint returned ${HTTP_CODE} instead of 200"
fi
echo ""

# Test 4: With valid API key (if provided)
if [ "$API_KEY" != "missing" ]; then
    echo "Test 4: Protected endpoint with API key"
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "x-api-key: ${API_KEY}" \
        "${BASE_URL}/events/search?limit=3")
    if [ "$HTTP_CODE" -eq 200 ]; then
        test_pass "Protected endpoint accessible with valid API key (200)"
    elif [ "$HTTP_CODE" -eq 403 ]; then
        test_fail "API key invalid or revoked (403)"
    elif [ "$HTTP_CODE" -eq 402 ]; then
        test_fail "API key plan insufficient (402)"
    else
        test_fail "Protected endpoint returned ${HTTP_CODE}"
    fi
    echo ""
    
    # Test 5: Fetch actual data
    echo "Test 5: Fetch event data"
    RESPONSE=$(curl -s -H "x-api-key: ${API_KEY}" \
        "${BASE_URL}/events/search?limit=3")
    if echo "$RESPONSE" | grep -q '"id"'; then
        test_pass "Successfully fetched event data"
        echo "$RESPONSE" | head -20
    else
        test_fail "Failed to fetch event data"
    fi
else
    test_warn "Skipping authenticated tests - Set RR_TEST_KEY environment variable to test with API key"
fi

echo ""
echo "=== Test Summary ==="
echo -e "${GREEN}Passed: ${PASS}${NC}"
echo -e "${RED}Failed: ${FAIL}${NC}"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
