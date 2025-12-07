#!/usr/bin/env python3
"""Seed script to create initial playbook templates."""

import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from releaseradar.db.session import get_db, close_db_session
from releaseradar.db.models import Playbook, PlaybookRule


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def seed_playbooks():
    """Create initial trading playbook templates."""
    session = get_db()
    try:
        existing_count = session.query(Playbook).count()
        if existing_count > 0:
            print(f"Playbooks already seeded ({existing_count} found). Skipping...")
            return

        playbooks = [
            {
                "title": "Earnings Beat Momentum",
                "category": "earnings",
                "description": "Long position after earnings beat with strong guidance. Best suited for growth stocks with positive surprise.",
                "setup_conditions": {
                    "event_types": ["earnings_beat", "guidance_raise"],
                    "conditions": [
                        "EPS beat by 10%+ vs consensus",
                        "Revenue beat by 5%+ vs consensus",
                        "Guidance raised for next quarter",
                        "Volume spike 2x+ average"
                    ]
                },
                "entry_logic": "Enter on first pullback to VWAP after initial gap up, or on break above pre-market high with volume confirmation.",
                "stop_template": "2% below entry or below gap support, whichever is tighter",
                "target_template": "Initial target: 10-15%. Extended: 25-30% for strong momentum",
                "holding_period": "3-10 days",
                "win_rate": 0.685,
                "avg_r": 2.1,
                "sample_size": 156,
                "visibility": "public",
            },
            {
                "title": "FDA Approval Breakout",
                "category": "fda",
                "description": "Aggressive long on FDA drug approval for biotech stocks. High risk/reward with catalyst confirmation.",
                "setup_conditions": {
                    "event_types": ["fda_approval"],
                    "conditions": [
                        "FDA approval received (NDA/BLA)",
                        "Drug addresses unmet medical need",
                        "Company has commercial infrastructure or partnership",
                        "Pre-approval stock not at 52-week high"
                    ]
                },
                "entry_logic": "Enter immediately on approval announcement if after hours, or at market open. Scale in over first 15 minutes.",
                "stop_template": "15% from entry (biotech volatility)",
                "target_template": "Scale out: 30% at +25%, 40% at +50%, trail final 30%",
                "holding_period": "2-5 days",
                "win_rate": 0.721,
                "avg_r": 3.2,
                "sample_size": 43,
                "visibility": "public",
            },
            {
                "title": "Insider Buying Accumulation",
                "category": "sec",
                "description": "Follow smart money with significant insider purchases. Multiple insiders or large CEO buy = strong signal.",
                "setup_conditions": {
                    "event_types": ["insider_buy", "form4_purchase"],
                    "conditions": [
                        "Insider purchase > $100K",
                        "Multiple insiders buying within 30 days",
                        "CEO/CFO involvement preferred",
                        "Stock not at 52-week high"
                    ]
                },
                "entry_logic": "Enter on first up day following Form 4 filing. Add on 3-5% pullbacks over next 2 weeks.",
                "stop_template": "10% from average entry price",
                "target_template": "Target 20-40% gain over 30-60 days",
                "holding_period": "30-60 days",
                "win_rate": 0.612,
                "avg_r": 1.8,
                "sample_size": 89,
                "visibility": "public",
            },
            {
                "title": "Guidance Cut Short",
                "category": "earnings",
                "description": "Short position on significant guidance reduction. Best on overvalued stocks with deteriorating fundamentals.",
                "setup_conditions": {
                    "event_types": ["guidance_cut", "earnings_miss"],
                    "conditions": [
                        "Guidance cut by 10%+ from prior",
                        "Stock was trading at premium valuation (P/E > sector)",
                        "Management commentary negative",
                        "No clear path to recovery cited"
                    ]
                },
                "entry_logic": "Short on bounce to VWAP or prior support-turned-resistance after gap down.",
                "stop_template": "5% above entry or above gap resistance",
                "target_template": "Target 15-25% decline. Extended for extreme cases.",
                "holding_period": "5-15 days",
                "win_rate": 0.583,
                "avg_r": 1.9,
                "sample_size": 67,
                "visibility": "public",
            },
            {
                "title": "M&A Arbitrage",
                "category": "corporate",
                "description": "Capture spread between current price and announced acquisition price. Low risk, moderate return.",
                "setup_conditions": {
                    "event_types": ["acquisition_announced", "merger"],
                    "conditions": [
                        "Deal announced with specific price",
                        "Buyer is credible with financing secured",
                        "Regulatory hurdles are manageable",
                        "Spread > 3% to close"
                    ]
                },
                "entry_logic": "Enter when spread to deal price > 5%. Size based on deal certainty assessment.",
                "stop_template": "Exit if spread widens to 15%+ (deal uncertainty)",
                "target_template": "Capture full spread to deal price minus 0.5% buffer",
                "holding_period": "30-180 days",
                "win_rate": 0.824,
                "avg_r": 1.2,
                "sample_size": 34,
                "visibility": "public",
            },
            {
                "title": "Dividend Increase Momentum",
                "category": "corporate",
                "description": "Long on significant dividend increase announcements. Signals management confidence and attracts income investors.",
                "setup_conditions": {
                    "event_types": ["dividend_increase", "special_dividend"],
                    "conditions": [
                        "Dividend increase > 10% from prior",
                        "Company has history of dividend growth",
                        "Payout ratio remains sustainable (<60%)",
                        "Free cash flow supports dividend"
                    ]
                },
                "entry_logic": "Enter on announcement day or first pullback within 3 days. Accumulate for income position.",
                "stop_template": "8% from entry or on dividend cut announcement",
                "target_template": "Hold indefinitely for income. Trim 25% on 25%+ gains",
                "holding_period": "6+ months",
                "win_rate": 0.718,
                "avg_r": 1.5,
                "sample_size": 112,
                "visibility": "public",
            },
            {
                "title": "Stock Buyback Catalyst",
                "category": "corporate",
                "description": "Long on significant buyback announcement. Company buying back shares is bullish signal with price support.",
                "setup_conditions": {
                    "event_types": ["buyback_announced", "buyback_increase"],
                    "conditions": [
                        "Buyback > 5% of shares outstanding",
                        "Company has cash/low leverage to execute",
                        "Stock trading below intrinsic value estimate",
                        "Management executing on prior buyback programs"
                    ]
                },
                "entry_logic": "Enter on announcement with half position. Add on 5% pullback if thesis intact.",
                "stop_template": "10% from entry",
                "target_template": "Gradual scaling out: 25% at +15%, 25% at +25%, hold remainder",
                "holding_period": "3-6 months",
                "win_rate": 0.645,
                "avg_r": 1.4,
                "sample_size": 78,
                "visibility": "public",
            },
            {
                "title": "SEC Filing Red Flag Short",
                "category": "sec",
                "description": "Short on concerning SEC filing disclosures. Material weaknesses, restatements, or auditor concerns.",
                "setup_conditions": {
                    "event_types": ["sec_10k_warning", "auditor_change", "restatement"],
                    "conditions": [
                        "Material weakness in internal controls disclosed",
                        "Auditor resignation or change mid-year",
                        "Financial restatement announced",
                        "Going concern warning"
                    ]
                },
                "entry_logic": "Short on any bounce following disclosure. Add on failed relief rally attempts.",
                "stop_template": "15% above entry (accounting issues can take time to price)",
                "target_template": "Target 25-40% decline. Can be more for fraud cases.",
                "holding_period": "7-30 days",
                "win_rate": 0.556,
                "avg_r": 2.5,
                "sample_size": 36,
                "visibility": "public",
            },
        ]

        for i, playbook_data in enumerate(playbooks):
            slug = slugify(playbook_data["title"])
            
            playbook = Playbook(
                slug=slug,
                title=playbook_data["title"],
                category=playbook_data["category"],
                description=playbook_data["description"],
                setup_conditions=playbook_data["setup_conditions"],
                entry_logic=playbook_data["entry_logic"],
                stop_template=playbook_data["stop_template"],
                target_template=playbook_data["target_template"],
                holding_period=playbook_data["holding_period"],
                win_rate=playbook_data["win_rate"],
                avg_r=playbook_data["avg_r"],
                sample_size=playbook_data["sample_size"],
                visibility=playbook_data["visibility"],
                display_order=i,
                is_active=True,
                is_featured=i < 3,
            )
            session.add(playbook)
            session.flush()

            event_types = playbook_data["setup_conditions"].get("event_types", [])
            for event_type in event_types:
                rule = PlaybookRule(
                    playbook_id=playbook.id,
                    rule_type="event_type",
                    operator="eq",
                    value=event_type,
                    is_required=True,
                    weight=1.0,
                )
                session.add(rule)

        session.commit()
        print(f"Successfully seeded {len(playbooks)} playbook templates!")

    except Exception as e:
        session.rollback()
        print(f"Error seeding playbooks: {e}")
        raise
    finally:
        close_db_session(session)


if __name__ == "__main__":
    seed_playbooks()
