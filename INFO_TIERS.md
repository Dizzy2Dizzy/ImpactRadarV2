# Information Tiers - Impact Radar

## Overview

Impact Radar classifies all market events into two information tiers to help users distinguish between direct market-moving events and contextual risk factors. This classification enables more intelligent filtering, scoring, and portfolio analysis.

## Tier Definitions

### Primary Tier
**Direct corporate/financial events linked to price movements**

Primary events are traditional market-moving catalysts that directly impact a company's stock price. These include regulatory filings, product approvals, earnings reports, and major corporate actions.

**Examples:**
- SEC filings (8-K, 10-Q, 10-K, S-1, etc.)
- FDA approvals and regulatory decisions
- Earnings releases and guidance updates
- M&A announcements
- Product launches and major contracts
- Executive changes
- Material legal/financial events

**Characteristics:**
- Company-specific
- Direct impact on financials or operations
- Mandatory disclosures or major announcements
- Historically correlated with price moves
- High actionability for investors

### Secondary Tier
**Contextual risk factors and environmental signals**

Secondary events provide contextual awareness of broader risks that may indirectly affect portfolio holdings. These include environmental risks, infrastructure failures, geopolitical events, and sector-wide pressures.

**Examples (Future Implementation):**
- Environmental disasters affecting facilities
- Cyber security incidents
- Supply chain disruptions
- Regulatory investigations
- Infrastructure failures
- Geopolitical tensions
- Sector-wide headwinds

**Characteristics:**
- May affect multiple companies
- Indirect or delayed impact
- Context for understanding risk exposure
- Lower immediate actionability
- Useful for risk management and scenario planning

## Info Subtypes

Each event is further classified with a subtype for granular filtering:

### Primary Subtypes
- `ipo` - Initial public offerings (S-1 filings)
- `earnings` - Quarterly/annual earnings (10-Q, 10-K)
- `material_event` - Material disclosures (8-K)
- `ma` - Mergers & acquisitions
- `regulatory_primary` - FDA approvals, primary regulatory actions
- `ownership_change` - Significant ownership changes
- `proxy` - Proxy statements and shareholder votes
- `financing` - Debt/equity financing events
- `product` - Product launches and updates
- `legal` - Legal proceedings and settlements
- `executive_change` - C-suite and board changes
- `announcement` - Major corporate announcements

### Secondary Subtypes (Future)
- `environmental` - Natural disasters, facility damage
- `cybersecurity` - Breaches, attacks
- `infrastructure` - Critical infrastructure failures
- `geopolitical` - Political instability, sanctions
- `supply_chain` - Supplier issues, logistics disruptions
- `regulatory_secondary` - Industry-wide regulatory changes

## API Usage

### Filtering by Tier

All event endpoints support the `info_tier` query parameter:

```bash
# Get only primary events (default)
GET /api/events/public?info_tier=primary

# Get only secondary events
GET /api/events/public?info_tier=secondary

# Get all events (backward compatible)
GET /api/events/public?info_tier=both
GET /api/events/public  # defaults to "both"
```

### Event Response Schema

All events now include tier information:

```json
{
  "id": 123,
  "ticker": "AAPL",
  "title": "Apple Files 10-Q",
  "event_type": "sec_10q",
  "info_tier": "primary",
  "info_subtype": "earnings",
  "impact_score": 75,
  "date": "2024-01-15T00:00:00Z",
  "context_risk_score": null,
  ...
}
```

### Context Risk Score

For events with contextual risk data (future feature), the `context_risk_score` field provides a 0-100 risk assessment:

- **0-33**: Low risk
- **34-66**: Medium risk
- **67-100**: High risk

```json
{
  "id": 456,
  "ticker": "TSLA",
  "title": "Factory Flood Risk",
  "info_tier": "secondary",
  "info_subtype": "environmental",
  "context_risk_score": 78,
  "context_signals": [
    {
      "signal_type": "weather",
      "severity": "high",
      "description": "Category 4 hurricane approaching"
    }
  ]
}
```

## UI Components

### InfoTierBadge

Displays a color-coded badge with tooltip:

- **Primary**: Blue badge with tooltip "Direct corporate/financial events linked to price moves"
- **Secondary**: Amber badge with tooltip "Contextual risk factors"

Shows subtype information when available (e.g., "Primary · IPO", "Secondary · Environmental")

### Event Filters

The EventsTab includes an "Information Tier" dropdown filter:
- **All Events** (default) - Shows both tiers
- **Primary Only** - Focus on actionable market events
- **Secondary Only** - Focus on risk context

### Portfolio View

The Portfolio view separates events by tier:
- **Upcoming Events** section shows primary tier events
- **Risk Context** section shows secondary tier events (when available)
- Context risk score displayed as color-coded meter

## Scoring Impact

Info tier affects event scoring through the `info_tier_factor`:

- **Primary tier**: `info_tier_factor = 0` (no adjustment)
- **Secondary tier**: `info_tier_factor = -5` (slight penalty, future)

This ensures primary events maintain their calculated scores while secondary events are slightly de-emphasized in overall rankings, reflecting their indirect impact.

## Classification Logic

Events are automatically classified by the `classify_info_tier()` function based on:

1. **Event Type** - Maps event_type to appropriate tier/subtype
2. **Source** - Validates source matches expected pattern (e.g., "SEC" for SEC filings)
3. **Fallback** - Defaults to primary tier with no subtype for unknown types

Classification happens automatically during event normalization in all scanners.

## Backward Compatibility

The tier system is fully backward compatible:

- Existing API calls without `info_tier` parameter default to `"both"`, returning all events as before
- All existing events are classified as `info_tier="primary"` by default
- Scoring remains unchanged for primary events (factor = 0)
- UI displays tier badges but maintains all existing functionality

## Use Cases

### For Active Traders
Filter to **Primary Only** to focus on immediate, actionable events that drive price movements.

### For Risk Managers
Filter to **Secondary Only** to monitor contextual risks affecting portfolio holdings.

### For Research Analysts
Use **All Events** view to understand both direct catalysts and environmental context.

### For Portfolio Monitoring
Review primary events for trading opportunities and secondary events for risk awareness.

## Future Enhancements

- **Context Signal Integration**: Add secondary events from environmental, cyber, and geopolitical sources
- **Multi-Company Secondary Events**: Link single secondary events to multiple affected tickers
- **Risk Scoring**: Develop ML models for context_risk_score calculation
- **Tier-Based Alerts**: Separate notification streams for primary vs secondary events
- **Historical Analysis**: Measure correlation between secondary signals and price impact

## Implementation Details

### Backend
- `backend/scanners/utils.py`: Classification logic in `classify_info_tier()`
- `backend/data_manager.py`: Tier-based filtering in `get_events()`
- `backend/analytics/scoring.py`: Tier factor calculation and context risk scoring
- `backend/api/schemas/events.py`: EventDetail schema with tier fields

### Frontend
- `marketing/components/dashboard/InfoTierBadge.tsx`: Badge component
- `marketing/components/dashboard/EventsTab.tsx`: Tier filtering UI
- `marketing/lib/api.ts`: API client with tier parameter support

### Database
- `info_tier` column on Event model (TEXT, default "primary")
- `info_subtype` column on Event model (TEXT, nullable)
- `context_signals` table for secondary event metadata

## Testing

Comprehensive test coverage in `backend/tests/test_info_tier.py`:
- Classification logic for all event types
- Auto-classification during normalization
- API filtering by tier
- Default behavior and backward compatibility

---

**Last Updated**: November 13, 2025 (Wave J Implementation)
