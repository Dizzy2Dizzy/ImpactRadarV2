"""
Insight Digest Generator Service - Creates daily/weekly market briefings.

Generates human-readable summaries like "How the market reacted to last week's FDA approvals"
and "Earnings playbook: Gap & Go vs Gap & Fade".
"""

from datetime import datetime, date, timedelta
from typing import Any, Optional
import statistics

from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session, joinedload

from releaseradar.db.models import (
    Event,
    EventPlaybookMatch,
    Playbook,
    InsightDigest,
    InsightDigestEvent,
    DigestSubscription,
    User,
)


class InsightDigestGenerator:
    """Service for generating daily and weekly insight digests."""

    def __init__(self, session: Session):
        self.session = session

    def generate_daily_digest(self, target_date: Optional[date] = None) -> dict:
        """
        Generate a daily digest for the previous trading day.
        Returns the created digest record.
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        period_start = target_date
        period_end = target_date

        return self._generate_digest("daily", period_start, period_end)

    def generate_weekly_digest(self, week_ending: Optional[date] = None) -> dict:
        """
        Generate a weekly digest for the previous week.
        Returns the created digest record.
        """
        if week_ending is None:
            today = date.today()
            days_since_sunday = today.weekday() + 1
            week_ending = today - timedelta(days=days_since_sunday)

        period_end = week_ending
        period_start = week_ending - timedelta(days=6)

        return self._generate_digest("weekly", period_start, period_end)

    def _generate_digest(self, cadence: str, period_start: date, period_end: date) -> dict:
        """Core digest generation logic."""
        existing = self.session.query(InsightDigest).filter(
            and_(
                InsightDigest.cadence == cadence,
                InsightDigest.period_start == period_start,
                InsightDigest.period_end == period_end,
            )
        ).first()

        if existing:
            return self._digest_to_dict(existing)

        events = self._get_period_events(period_start, period_end)

        if not events:
            digest = InsightDigest(
                cadence=cadence,
                period_start=period_start,
                period_end=period_end,
                subject=self._generate_subject(cadence, period_start, period_end, 0),
                headline="No significant events this period",
                total_events=0,
                status="generated",
                generated_at=datetime.utcnow(),
            )
            self.session.add(digest)
            self.session.commit()
            return self._digest_to_dict(digest)

        stats = self._calculate_period_stats(events)
        top_events = self._select_notable_events(events, limit=10)
        playbook_stats = self._calculate_playbook_performance(period_start, period_end)
        highlights = self._generate_highlights(events, stats, playbook_stats, cadence)

        subject = self._generate_subject(cadence, period_start, period_end, len(events))
        headline = self._generate_headline(stats, cadence)
        html_body = self._generate_html_body(highlights, top_events, stats, playbook_stats, cadence)
        text_body = self._generate_text_body(highlights, top_events, stats)

        digest = InsightDigest(
            cadence=cadence,
            period_start=period_start,
            period_end=period_end,
            subject=subject,
            headline=headline,
            html_body=html_body,
            text_body=text_body,
            highlights=highlights,
            playbook_stats=playbook_stats,
            total_events=len(events),
            avg_move_1d=stats.get("avg_move_1d"),
            avg_move_5d=stats.get("avg_move_5d"),
            top_sectors=stats.get("top_sectors"),
            top_event_types=stats.get("top_event_types"),
            status="generated",
            generated_at=datetime.utcnow(),
        )
        self.session.add(digest)
        self.session.flush()

        for idx, event in enumerate(top_events):
            digest_event = InsightDigestEvent(
                digest_id=digest.id,
                event_id=event["id"],
                ordering=idx,
                summary=self._generate_event_summary(event),
                stats={
                    "move_1d": event.get("realized_return_1d"),
                    "impact_score": event.get("impact_score"),
                    "direction": event.get("direction"),
                },
                section=self._categorize_event(event),
            )
            self.session.add(digest_event)

        self.session.commit()
        return self._digest_to_dict(digest)

    def get_latest_digest(self, cadence: str) -> Optional[dict]:
        """Get the most recent digest of a given cadence."""
        digest = (
            self.session.query(InsightDigest)
            .filter(InsightDigest.cadence == cadence)
            .order_by(desc(InsightDigest.period_end))
            .first()
        )
        return self._digest_to_dict(digest) if digest else None

    def get_digest_by_id(self, digest_id: int) -> Optional[dict]:
        """Get a specific digest by ID."""
        digest = (
            self.session.query(InsightDigest)
            .options(joinedload(InsightDigest.events))
            .filter(InsightDigest.id == digest_id)
            .first()
        )
        return self._digest_to_dict(digest) if digest else None

    def list_digests(self, cadence: Optional[str] = None, limit: int = 20, offset: int = 0) -> list[dict]:
        """List digests with optional filtering."""
        query = self.session.query(InsightDigest)

        if cadence:
            query = query.filter(InsightDigest.cadence == cadence)

        digests = (
            query.order_by(desc(InsightDigest.period_end))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [self._digest_to_dict(d) for d in digests]

    def get_subscribers(self, cadence: str) -> list[dict]:
        """Get all active subscribers for a digest cadence."""
        subs = (
            self.session.query(DigestSubscription)
            .options(joinedload(DigestSubscription.user))
            .filter(
                and_(
                    DigestSubscription.frequency == cadence,
                    DigestSubscription.active == True,
                )
            )
            .all()
        )

        return [
            {
                "subscription_id": s.id,
                "user_id": s.user_id,
                "email": s.user.email if s.user else None,
                "delivery_time": s.delivery_time,
                "include_sections": s.include_sections,
                "min_score_threshold": s.min_score_threshold,
            }
            for s in subs
        ]

    def mark_digest_sent(self, digest_id: int, recipients_count: int) -> bool:
        """Mark a digest as sent."""
        digest = self.session.query(InsightDigest).filter(InsightDigest.id == digest_id).first()
        if not digest:
            return False

        digest.status = "sent"
        digest.sent_at = datetime.utcnow()
        digest.recipients_count = recipients_count
        self.session.commit()
        return True

    def _get_period_events(self, period_start: date, period_end: date) -> list[dict]:
        """Get all events within the specified period."""
        start_datetime = datetime.combine(period_start, datetime.min.time())
        end_datetime = datetime.combine(period_end, datetime.max.time())

        events = (
            self.session.query(Event)
            .filter(
                and_(
                    Event.date >= start_datetime,
                    Event.date <= end_datetime,
                )
            )
            .order_by(desc(Event.impact_score))
            .all()
        )

        return [self._event_to_dict(e) for e in events]

    def _calculate_period_stats(self, events: list[dict]) -> dict:
        """Calculate aggregate statistics for the period."""
        if not events:
            return {}

        moves_1d = [e["realized_return_1d"] for e in events if e.get("realized_return_1d") is not None]
        avg_move_1d = statistics.mean(moves_1d) if moves_1d else None

        sectors = {}
        event_types = {}
        directions = {"positive": 0, "negative": 0, "neutral": 0}

        for e in events:
            sector = e.get("sector") or "Other"
            sectors[sector] = sectors.get(sector, 0) + 1

            event_type = e.get("event_type") or "unknown"
            event_types[event_type] = event_types.get(event_type, 0) + 1

            direction = e.get("direction") or "neutral"
            if direction in directions:
                directions[direction] += 1

        top_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:5]
        top_event_types = sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_events": len(events),
            "avg_move_1d": round(avg_move_1d, 2) if avg_move_1d else None,
            "avg_move_5d": None,
            "top_sectors": [{"sector": s, "count": c} for s, c in top_sectors],
            "top_event_types": [{"type": t, "count": c} for t, c in top_event_types],
            "direction_breakdown": directions,
            "avg_impact_score": round(statistics.mean([e["impact_score"] for e in events if e.get("impact_score")]), 1) if events else None,
        }

    def _select_notable_events(self, events: list[dict], limit: int = 10) -> list[dict]:
        """Select the most notable events for featuring."""
        scored_events = []
        for e in events:
            score = 0
            score += (e.get("impact_score") or 0) * 1.0

            if e.get("realized_return_1d"):
                score += abs(e["realized_return_1d"]) * 10

            if e.get("is_featured"):
                score += 20

            scored_events.append((score, e))

        scored_events.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored_events[:limit]]

    def _calculate_playbook_performance(self, period_start: date, period_end: date) -> list[dict]:
        """Calculate playbook performance for the period."""
        start_datetime = datetime.combine(period_start, datetime.min.time())
        end_datetime = datetime.combine(period_end, datetime.max.time())

        matches = (
            self.session.query(EventPlaybookMatch)
            .options(
                joinedload(EventPlaybookMatch.playbook),
                joinedload(EventPlaybookMatch.event),
            )
            .join(Event)
            .filter(
                and_(
                    Event.date >= start_datetime,
                    Event.date <= end_datetime,
                )
            )
            .all()
        )

        playbook_stats = {}
        for m in matches:
            if not m.playbook:
                continue

            pb_id = m.playbook_id
            if pb_id not in playbook_stats:
                playbook_stats[pb_id] = {
                    "playbook_id": pb_id,
                    "playbook_title": m.playbook.title,
                    "playbook_slug": m.playbook.slug,
                    "matches": 0,
                    "returns": [],
                }

            playbook_stats[pb_id]["matches"] += 1
            if m.event and m.event.realized_return_1d is not None:
                playbook_stats[pb_id]["returns"].append(m.event.realized_return_1d)

        result = []
        for ps in playbook_stats.values():
            returns = ps["returns"]
            avg_return = round(statistics.mean(returns), 2) if returns else None
            win_rate = round(len([r for r in returns if r > 0]) / len(returns), 2) if returns else None

            result.append({
                "playbook_id": ps["playbook_id"],
                "playbook_title": ps["playbook_title"],
                "playbook_slug": ps["playbook_slug"],
                "matches": ps["matches"],
                "avg_return_1d": avg_return,
                "win_rate": win_rate,
            })

        result.sort(key=lambda x: x["matches"], reverse=True)
        return result[:5]

    def _generate_highlights(self, events: list[dict], stats: dict, playbook_stats: list, cadence: str) -> list[dict]:
        """Generate key insight highlights."""
        highlights = []

        if stats.get("total_events"):
            highlights.append({
                "type": "summary",
                "title": f"{stats['total_events']} Events Tracked",
                "text": f"Impact Radar tracked {stats['total_events']} significant events this {'day' if cadence == 'daily' else 'week'}.",
            })

        if stats.get("avg_move_1d") is not None:
            direction_word = "up" if stats["avg_move_1d"] > 0 else "down"
            highlights.append({
                "type": "market_move",
                "title": f"Average 1-Day Move: {abs(stats['avg_move_1d']):.2f}%",
                "text": f"Stocks moved an average of {abs(stats['avg_move_1d']):.2f}% {direction_word} following events.",
            })

        if stats.get("top_event_types"):
            top_type = stats["top_event_types"][0]
            highlights.append({
                "type": "event_type",
                "title": f"Most Active: {top_type['type'].replace('_', ' ').title()}",
                "text": f"{top_type['count']} {top_type['type'].replace('_', ' ')} events dominated the period.",
            })

        if playbook_stats:
            top_pb = playbook_stats[0]
            highlights.append({
                "type": "playbook",
                "title": f"Top Playbook: {top_pb['playbook_title']}",
                "text": f"Matched {top_pb['matches']} events with {(top_pb['win_rate'] or 0) * 100:.0f}% win rate.",
            })

        return highlights

    def _generate_subject(self, cadence: str, period_start: date, period_end: date, event_count: int) -> str:
        """Generate email subject line."""
        if cadence == "daily":
            return f"Impact Radar Daily: {event_count} Events on {period_start.strftime('%b %d')}"
        else:
            return f"Impact Radar Weekly: {period_start.strftime('%b %d')} - {period_end.strftime('%b %d')}"

    def _generate_headline(self, stats: dict, cadence: str) -> str:
        """Generate main headline."""
        total = stats.get("total_events", 0)
        avg_move = stats.get("avg_move_1d")

        if avg_move and avg_move > 1:
            return f"Strong Market Reactions: Avg +{avg_move:.1f}% Move"
        elif avg_move and avg_move < -1:
            return f"Bearish Reactions: Avg {avg_move:.1f}% Move"
        else:
            return f"{total} Market Events {'Today' if cadence == 'daily' else 'This Week'}"

    def _generate_html_body(self, highlights: list, top_events: list, stats: dict, playbook_stats: list, cadence: str) -> str:
        """Generate HTML email body."""
        html_parts = [
            "<!DOCTYPE html><html><head><style>",
            "body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }",
            ".highlight { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; }",
            ".event { border-left: 3px solid #0066cc; padding-left: 12px; margin: 15px 0; }",
            ".positive { color: #22c55e; } .negative { color: #ef4444; }",
            "h1 { color: #1a1a2e; } h2 { color: #16213e; border-bottom: 2px solid #0066cc; padding-bottom: 8px; }",
            "</style></head><body>",
        ]

        html_parts.append(f"<h1>Impact Radar {'Daily' if cadence == 'daily' else 'Weekly'} Insights</h1>")

        if highlights:
            html_parts.append("<h2>Key Highlights</h2>")
            for h in highlights:
                html_parts.append(f'<div class="highlight"><strong>{h["title"]}</strong><p>{h["text"]}</p></div>')

        if top_events:
            html_parts.append("<h2>Notable Events</h2>")
            for e in top_events[:5]:
                direction_class = "positive" if e.get("direction") == "positive" else "negative" if e.get("direction") == "negative" else ""
                move = e.get("realized_return_1d")
                move_str = f"{move:+.2f}%" if move else "N/A"
                html_parts.append(
                    f'<div class="event">'
                    f'<strong>{e["ticker"]}</strong> - {e["title"][:80]}<br>'
                    f'Score: {e.get("impact_score", "N/A")} | '
                    f'<span class="{direction_class}">1D Move: {move_str}</span>'
                    f'</div>'
                )

        if playbook_stats:
            html_parts.append("<h2>Playbook Performance</h2>")
            for pb in playbook_stats[:3]:
                wr = pb.get("win_rate")
                wr_str = f"{wr * 100:.0f}%" if wr else "N/A"
                html_parts.append(
                    f'<div class="highlight">'
                    f'<strong>{pb["playbook_title"]}</strong><br>'
                    f'Matches: {pb["matches"]} | Win Rate: {wr_str}'
                    f'</div>'
                )

        html_parts.append("<p style='color:#666;font-size:12px;margin-top:30px;'>Generated by Impact Radar</p>")
        html_parts.append("</body></html>")

        return "".join(html_parts)

    def _generate_text_body(self, highlights: list, top_events: list, stats: dict) -> str:
        """Generate plain text email body."""
        lines = ["IMPACT RADAR INSIGHTS", "=" * 40, ""]

        if highlights:
            lines.append("KEY HIGHLIGHTS")
            lines.append("-" * 20)
            for h in highlights:
                lines.append(f"* {h['title']}")
                lines.append(f"  {h['text']}")
                lines.append("")

        if top_events:
            lines.append("NOTABLE EVENTS")
            lines.append("-" * 20)
            for e in top_events[:5]:
                move = e.get("realized_return_1d")
                move_str = f"{move:+.2f}%" if move else "N/A"
                lines.append(f"* {e['ticker']} - {e['title'][:60]}")
                lines.append(f"  Score: {e.get('impact_score', 'N/A')} | 1D Move: {move_str}")
                lines.append("")

        return "\n".join(lines)

    def _generate_event_summary(self, event: dict) -> str:
        """Generate a brief narrative summary for an event."""
        ticker = event.get("ticker", "")
        event_type = event.get("event_type", "event").replace("_", " ")
        move = event.get("realized_return_1d")

        if move:
            direction = "gained" if move > 0 else "dropped"
            return f"{ticker} {direction} {abs(move):.1f}% following {event_type}"
        return f"{ticker} reported {event_type}"

    def _categorize_event(self, event: dict) -> str:
        """Categorize an event for digest sections."""
        event_type = event.get("event_type", "").lower()

        if "fda" in event_type or "approval" in event_type:
            return "fda_roundup"
        elif "earnings" in event_type:
            return "earnings_watch"
        elif "8k" in event_type or "sec" in event_type:
            return "sec_filings"
        else:
            return "top_movers"

    def _event_to_dict(self, event: Event) -> dict:
        """Convert Event ORM to dict."""
        return {
            "id": event.id,
            "ticker": event.ticker,
            "company_name": event.company_name,
            "title": event.title,
            "event_type": event.event_type,
            "date": event.date.isoformat() if event.date else None,
            "impact_score": event.impact_score,
            "direction": event.direction,
            "confidence": event.confidence,
            "sector": event.sector,
            "realized_return_1d": event.realized_return_1d,
            "source_url": event.source_url,
        }

    def _digest_to_dict(self, digest: InsightDigest) -> dict:
        """Convert InsightDigest ORM to dict."""
        if not digest:
            return None

        return {
            "id": digest.id,
            "cadence": digest.cadence,
            "period_start": digest.period_start.isoformat() if digest.period_start else None,
            "period_end": digest.period_end.isoformat() if digest.period_end else None,
            "subject": digest.subject,
            "headline": digest.headline,
            "html_body": digest.html_body,
            "text_body": digest.text_body,
            "highlights": digest.highlights,
            "playbook_stats": digest.playbook_stats,
            "total_events": digest.total_events,
            "avg_move_1d": digest.avg_move_1d,
            "avg_move_5d": digest.avg_move_5d,
            "top_sectors": digest.top_sectors,
            "top_event_types": digest.top_event_types,
            "status": digest.status,
            "generated_at": digest.generated_at.isoformat() if digest.generated_at else None,
            "sent_at": digest.sent_at.isoformat() if digest.sent_at else None,
            "recipients_count": digest.recipients_count,
            "created_at": digest.created_at.isoformat() if digest.created_at else None,
            "events": [
                {
                    "id": e.id,
                    "event_id": e.event_id,
                    "ordering": e.ordering,
                    "summary": e.summary,
                    "stats": e.stats,
                    "section": e.section,
                }
                for e in (digest.events or [])
            ] if hasattr(digest, "events") and digest.events else [],
        }
