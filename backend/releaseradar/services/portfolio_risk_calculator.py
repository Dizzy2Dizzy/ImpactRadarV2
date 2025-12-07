"""
Portfolio Risk Calculator Service

Calculates comprehensive risk metrics for user portfolios including:
- Event exposure (% of portfolio exposed to upcoming events)
- Concentration risk (Herfindahl index)
- Sector diversification (entropy-based score)
- Value at Risk (VaR) at 95% confidence
- Expected Shortfall (CVaR)
- Event-level exposure tracking
"""

from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging
import numpy as np
from collections import defaultdict
import math

from releaseradar.db.models import (
    UserPortfolio,
    PortfolioPosition,
    PortfolioRiskSnapshot,
    PortfolioEventExposure,
    Event,
    PriceHistory,
    Company,
)

logger = logging.getLogger(__name__)


def calculate_portfolio_risk(
    portfolio_id: int,
    db: Session,
    lookforward_days: int = 30
) -> PortfolioRiskSnapshot:
    """
    Calculate comprehensive risk metrics for a portfolio.
    
    Args:
        portfolio_id: ID of the portfolio to analyze
        db: Database session
        lookforward_days: Days to look ahead for event exposure (default: 30)
    
    Returns:
        PortfolioRiskSnapshot: Risk snapshot with all calculated metrics
    
    Raises:
        ValueError: If portfolio not found or has no positions
    """
    # Get portfolio and positions
    portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")
    
    positions = db.query(PortfolioPosition).filter(
        PortfolioPosition.portfolio_id == portfolio_id
    ).all()
    
    if not positions:
        logger.warning(f"Portfolio {portfolio_id} has no positions, creating empty risk snapshot")
        # Create empty snapshot for portfolios with no positions
        snapshot = PortfolioRiskSnapshot(
            portfolio_id=portfolio_id,
            snapshot_date=datetime.utcnow(),
            total_event_exposure=0.0,
            concentration_risk_score=0.0,
            sector_diversification_score=100.0,  # Perfect diversification when empty
            var_95=0.0,
            expected_shortfall=0.0,
            top_event_risks_json=[],
            correlation_matrix_json={}
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    
    # Calculate total portfolio value
    total_value = sum(pos.qty * pos.avg_price for pos in positions)
    
    if total_value <= 0:
        raise ValueError(f"Portfolio {portfolio_id} has invalid total value: {total_value}")
    
    # Get upcoming events (next 30 days)
    event_window_start = datetime.utcnow()
    event_window_end = datetime.utcnow() + timedelta(days=lookforward_days)
    
    tickers = [pos.ticker for pos in positions]
    upcoming_events = db.query(Event).filter(
        and_(
            Event.ticker.in_(tickers),
            Event.date >= event_window_start,
            Event.date <= event_window_end
        )
    ).all()
    
    # Calculate event exposure (% of portfolio with upcoming events)
    tickers_with_events = set(e.ticker for e in upcoming_events)
    exposure_value = sum(
        pos.qty * pos.avg_price 
        for pos in positions 
        if pos.ticker in tickers_with_events
    )
    total_event_exposure = (exposure_value / total_value) * 100 if total_value > 0 else 0.0
    
    # Calculate concentration risk (Herfindahl index: 0-100, higher = more concentrated)
    position_weights = [(pos.qty * pos.avg_price) / total_value for pos in positions]
    herfindahl_index = sum(w ** 2 for w in position_weights)
    # Normalize to 0-100 scale (0 = perfectly diversified, 100 = single position)
    # For reference: 1/n positions equally weighted gives H=1/n
    # Perfect diversification (infinite positions) → H=0, Single position → H=1
    concentration_risk_score = herfindahl_index * 100
    
    # Calculate sector diversification score (entropy-based, 0-100, higher = more diversified)
    sector_diversification_score = _calculate_sector_diversification(positions, db, total_value)
    
    # Calculate VaR and Expected Shortfall with data quality metadata
    var_95, expected_shortfall, data_quality_metadata = _calculate_var_and_es(positions, db)
    
    # Identify top 10 event risks
    top_event_risks = _calculate_top_event_risks(
        positions, 
        upcoming_events, 
        total_value, 
        db,
        top_n=10
    )
    
    # Create risk snapshot
    snapshot = PortfolioRiskSnapshot(
        portfolio_id=portfolio_id,
        snapshot_date=datetime.utcnow(),
        total_event_exposure=total_event_exposure,
        concentration_risk_score=concentration_risk_score,
        sector_diversification_score=sector_diversification_score,
        var_95=var_95,
        expected_shortfall=expected_shortfall,
        top_event_risks_json=top_event_risks,
        correlation_matrix_json=data_quality_metadata
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    logger.info(
        f"Created risk snapshot for portfolio {portfolio_id}: "
        f"event_exposure={total_event_exposure:.2f}%, "
        f"concentration={concentration_risk_score:.2f}, "
        f"var_95={var_95:.2f}%"
    )
    
    return snapshot


def calculate_event_exposure(
    portfolio_id: int,
    event_id: int,
    db: Session
) -> PortfolioEventExposure:
    """
    Calculate exposure for a specific event affecting a portfolio position.
    
    Args:
        portfolio_id: ID of the portfolio
        event_id: ID of the event
        db: Database session
    
    Returns:
        PortfolioEventExposure: Calculated event exposure record
    
    Raises:
        ValueError: If portfolio, event, or position not found
    """
    # Get portfolio
    portfolio = db.query(UserPortfolio).filter(UserPortfolio.id == portfolio_id).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")
    
    # Get event
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found")
    
    # Get position for event's ticker
    position = db.query(PortfolioPosition).filter(
        and_(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.ticker == event.ticker
        )
    ).first()
    
    if not position:
        raise ValueError(
            f"No position found for ticker {event.ticker} in portfolio {portfolio_id}"
        )
    
    # Calculate total portfolio value
    all_positions = db.query(PortfolioPosition).filter(
        PortfolioPosition.portfolio_id == portfolio_id
    ).all()
    total_value = sum(pos.qty * pos.avg_price for pos in all_positions)
    
    if total_value <= 0:
        raise ValueError(f"Portfolio {portfolio_id} has invalid total value: {total_value}")
    
    # Calculate position metrics
    position_value = position.qty * position.avg_price
    position_size_pct = (position_value / total_value) * 100
    
    # Estimate impact % from event score
    # Use ML-adjusted score if available, otherwise use impact_score
    event_score = event.ml_adjusted_score if event.ml_adjusted_score else event.impact_score
    
    # Convert score (0-100) to estimated impact % (conservative estimate)
    # High score (80-100) → 5-10% impact
    # Medium score (50-79) → 2-5% impact
    # Low score (0-49) → 0.5-2% impact
    if event_score >= 80:
        estimated_impact_pct = 5.0 + (event_score - 80) * 0.25  # 5-10%
    elif event_score >= 50:
        estimated_impact_pct = 2.0 + (event_score - 50) * 0.1   # 2-5%
    else:
        estimated_impact_pct = 0.5 + (event_score / 50) * 1.5   # 0.5-2%
    
    # Apply directional adjustment if available
    if event.direction:
        if event.direction.lower() == "negative":
            estimated_impact_pct = -abs(estimated_impact_pct)
        elif event.direction.lower() == "positive":
            estimated_impact_pct = abs(estimated_impact_pct)
    
    # Calculate dollar exposure
    dollar_exposure = position_value * (abs(estimated_impact_pct) / 100)
    
    # Generate hedge recommendation if exposure is significant
    hedge_recommendation = _generate_hedge_recommendation(
        position=position,
        event=event,
        position_size_pct=position_size_pct,
        estimated_impact_pct=estimated_impact_pct,
        dollar_exposure=dollar_exposure
    )
    
    # Create or update exposure record
    exposure = PortfolioEventExposure(
        portfolio_id=portfolio_id,
        position_id=position.id,
        event_id=event_id,
        position_size_pct=position_size_pct,
        estimated_impact_pct=estimated_impact_pct,
        dollar_exposure=dollar_exposure,
        hedge_recommendation=hedge_recommendation,
        calculated_at=datetime.utcnow()
    )
    
    db.add(exposure)
    db.commit()
    db.refresh(exposure)
    
    logger.info(
        f"Created event exposure for portfolio {portfolio_id}, event {event_id}: "
        f"position={position_size_pct:.2f}%, impact={estimated_impact_pct:.2f}%, "
        f"dollar_risk=${dollar_exposure:.2f}"
    )
    
    return exposure


def _calculate_sector_diversification(
    positions: List[PortfolioPosition],
    db: Session,
    total_value: float
) -> float:
    """
    Calculate sector diversification score using Shannon entropy.
    
    Returns:
        float: Diversification score (0-100, higher = more diversified)
    """
    # Get sector allocation for each position
    sector_values = defaultdict(float)
    
    for pos in positions:
        company = db.query(Company).filter(Company.ticker == pos.ticker).first()
        sector = company.sector if company and company.sector else "Unknown"
        sector_values[sector] += pos.qty * pos.avg_price
    
    # Calculate sector weights
    sector_weights = [v / total_value for v in sector_values.values()]
    
    # Calculate Shannon entropy
    entropy = 0.0
    for w in sector_weights:
        if w > 0:
            entropy -= w * math.log(w)
    
    # Normalize to 0-100 scale
    # Max entropy for n sectors = log(n)
    # Single sector → entropy=0, Perfectly diversified across n sectors → entropy=log(n)
    n_sectors = len(sector_values)
    if n_sectors <= 1:
        return 0.0  # Single sector = no diversification
    
    max_entropy = math.log(n_sectors)
    diversification_score = (entropy / max_entropy) * 100 if max_entropy > 0 else 0.0
    
    return diversification_score


def _calculate_var_and_es(
    positions: List[PortfolioPosition],
    db: Session,
    confidence: float = 0.95,
    lookback_days: int = 252  # 1 trading year
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Calculate Value at Risk (VaR) and Expected Shortfall (CVaR) using logarithmic returns.
    
    Uses log returns instead of simple returns for more accurate risk estimation:
    - log_return = ln(price[t] / price[t-1])
    - Log returns are more appropriate for VaR/ES as they are time-additive
    - Prevents inflated risk numbers from raw price differences
    
    Adaptive calculation strategy:
    - Minimum 10 days required (down from 30)
    - 10-29 days: Calculate VaR with confidence adjustment factor sqrt(30/actual_days)
    - < 10 days: Use market-wide average volatility estimate
    
    Args:
        positions: List of portfolio positions
        db: Database session
        confidence: Confidence level for VaR (default: 0.95)
        lookback_days: Number of trading days to look back (default: 252)
    
    Returns:
        Tuple[float, float, Dict]: (var_95, expected_shortfall, data_quality_metadata)
    """
    # Get historical returns for each position
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days * 2)  # Extra buffer for weekends
    
    position_returns = []
    position_weights = []
    position_data_quality = []
    total_value = sum(pos.qty * pos.avg_price for pos in positions)
    
    # Track data quality
    positions_with_full_data = 0
    positions_with_limited_data = 0
    positions_with_minimal_data = 0
    positions_without_data = 0
    
    # First pass: collect all volatilities for market-wide estimate
    all_volatilities = []
    
    for pos in positions:
        # Get price history from database (no external API calls)
        prices = db.query(PriceHistory).filter(
            and_(
                PriceHistory.ticker == pos.ticker,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date
            )
        ).order_by(PriceHistory.date).all()
        
        if len(prices) < 2:
            continue
        
        # Calculate returns for volatility estimation
        daily_returns = []
        for i in range(1, len(prices)):
            if prices[i-1].close <= 0 or prices[i].close <= 0:
                continue
            try:
                log_ret = np.log(prices[i].close / prices[i-1].close)
                if np.isfinite(log_ret):
                    daily_returns.append(log_ret)
            except (ValueError, ZeroDivisionError):
                continue
        
        if len(daily_returns) >= 2:
            volatility = np.std(daily_returns)
            if np.isfinite(volatility) and volatility > 0:
                all_volatilities.append(volatility)
    
    # Calculate market-wide average volatility for fallback
    market_avg_volatility = np.mean(all_volatilities) if all_volatilities else 0.02
    
    logger.info(
        f"Market-wide average volatility: {market_avg_volatility:.4f} "
        f"(from {len(all_volatilities)} positions)"
    )
    
    # Second pass: calculate position-specific VaR with adaptive strategy
    for pos in positions:
        # Get price history from database (no external API calls)
        prices = db.query(PriceHistory).filter(
            and_(
                PriceHistory.ticker == pos.ticker,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date
            )
        ).order_by(PriceHistory.date).all()
        
        if len(prices) < 2:
            logger.info(
                f"No price history for {pos.ticker} "
                f"({len(prices)} days), using market-wide volatility estimate"
            )
            positions_without_data += 1
            continue
        
        # Calculate logarithmic returns (ln(P[t] / P[t-1]))
        # More accurate than simple returns for risk calculations
        daily_returns = []
        for i in range(1, len(prices)):
            # Check for invalid prices
            if prices[i-1].close <= 0 or prices[i].close <= 0:
                continue
            
            try:
                # Calculate logarithmic return
                log_ret = np.log(prices[i].close / prices[i-1].close)
                
                # Filter out invalid values (NaN, inf)
                if np.isfinite(log_ret):
                    daily_returns.append(log_ret)
            except (ValueError, ZeroDivisionError):
                continue
        
        num_returns = len(daily_returns)
        weight = (pos.qty * pos.avg_price) / total_value
        
        # Adaptive strategy based on available data
        if num_returns >= 30:
            # Full data: use as-is
            position_returns.append(daily_returns)
            position_weights.append(weight)
            position_data_quality.append({
                "ticker": pos.ticker,
                "data_days": num_returns,
                "quality": "full",
                "adjustment_factor": 1.0
            })
            positions_with_full_data += 1
            logger.info(
                f"{pos.ticker}: {num_returns} days of data (full quality)"
            )
        
        elif num_returns >= 10:
            # Limited data (10-29 days): apply confidence adjustment
            # Adjustment factor: sqrt(30/actual_days) to account for uncertainty
            adjustment_factor = np.sqrt(30.0 / num_returns)
            
            # Adjust returns by multiplying by adjustment factor
            adjusted_returns = [r * adjustment_factor for r in daily_returns]
            position_returns.append(adjusted_returns)
            position_weights.append(weight)
            position_data_quality.append({
                "ticker": pos.ticker,
                "data_days": num_returns,
                "quality": "limited",
                "adjustment_factor": adjustment_factor
            })
            positions_with_limited_data += 1
            logger.info(
                f"{pos.ticker}: {num_returns} days of data (limited quality, "
                f"adjustment factor: {adjustment_factor:.2f})"
            )
        
        else:
            # Minimal data (< 10 days): use market-wide volatility estimate
            # Generate synthetic returns based on market average volatility
            # Use normal distribution with market volatility
            num_synthetic_returns = 30
            synthetic_returns = list(np.random.normal(0, market_avg_volatility, num_synthetic_returns))
            
            position_returns.append(synthetic_returns)
            position_weights.append(weight)
            position_data_quality.append({
                "ticker": pos.ticker,
                "data_days": num_returns,
                "quality": "minimal",
                "adjustment_factor": None,
                "method": "market_volatility_estimate"
            })
            positions_with_minimal_data += 1
            logger.info(
                f"{pos.ticker}: {num_returns} days of data (minimal quality, "
                f"using market volatility estimate: {market_avg_volatility:.4f})"
            )
    
    # Build data quality metadata
    data_quality_metadata = {
        "positions_analyzed": len(positions),
        "positions_with_full_data": positions_with_full_data,
        "positions_with_limited_data": positions_with_limited_data,
        "positions_with_minimal_data": positions_with_minimal_data,
        "positions_without_data": positions_without_data,
        "market_avg_volatility": round(market_avg_volatility, 4),
        "position_details": position_data_quality,
        "calculation_method": "adaptive_var"
    }
    
    # Fallback to conservative estimates if no data at all
    if not position_returns:
        logger.info(
            f"No price history for VaR calculation across all positions. "
            f"Positions without data: {positions_without_data}. "
            f"Returning conservative default estimates based on typical market volatility."
        )
        data_quality_metadata["var_method"] = "default_estimate"
        data_quality_metadata["data_quality_warning"] = "No historical data available for any positions"
        # Return conservative default estimates based on typical market volatility
        # ~1.5% daily VaR and ~2.0% ES are reasonable defaults for diversified portfolios
        return 1.5, 2.0, data_quality_metadata
    
    logger.info(
        f"VaR calculation: {positions_with_full_data} full data, "
        f"{positions_with_limited_data} limited data, "
        f"{positions_with_minimal_data} minimal data, "
        f"{positions_without_data} no data"
    )
    
    # Calculate portfolio returns (weighted sum)
    # Align all return series to same length (use minimum)
    min_length = min(len(r) for r in position_returns)
    portfolio_returns = []
    
    for i in range(min_length):
        try:
            portfolio_ret = sum(
                position_returns[j][i] * position_weights[j] 
                for j in range(len(position_returns))
            )
            if np.isfinite(portfolio_ret):
                portfolio_returns.append(portfolio_ret)
        except (IndexError, ValueError) as e:
            logger.warning(f"Error calculating portfolio return at index {i}: {e}")
            continue
    
    if not portfolio_returns or len(portfolio_returns) < 2:
        logger.info(
            f"Insufficient portfolio returns ({len(portfolio_returns)}) for VaR calculation. "
            f"Returning conservative default estimates."
        )
        data_quality_metadata["var_method"] = "default_estimate"
        data_quality_metadata["data_quality_warning"] = "Insufficient portfolio returns after aggregation"
        return 1.5, 2.0, data_quality_metadata
    
    # Add data quality indicators
    data_quality_metadata["portfolio_returns_count"] = len(portfolio_returns)
    
    if positions_with_full_data == len(positions):
        data_quality_metadata["overall_quality"] = "high"
    elif positions_with_limited_data > 0 or positions_with_minimal_data > 0:
        data_quality_metadata["overall_quality"] = "medium"
        data_quality_metadata["data_quality_warning"] = (
            f"Risk estimates based on limited data: "
            f"{positions_with_limited_data} positions with 10-29 days, "
            f"{positions_with_minimal_data} positions with <10 days (using market volatility)"
        )
    else:
        data_quality_metadata["overall_quality"] = "low"
    
    # Calculate VaR at specified confidence level
    sorted_returns = sorted(portfolio_returns)
    var_index = int(len(sorted_returns) * (1 - confidence))
    
    # Ensure valid index
    if var_index < 0 or var_index >= len(sorted_returns):
        var_index = max(0, min(var_index, len(sorted_returns) - 1))
    
    # VaR is the absolute value of the loss at the confidence level
    var_95 = float(abs(sorted_returns[var_index]) * 100)  # Convert to percentage, ensure Python float
    
    # Calculate Expected Shortfall (average of returns beyond VaR)
    # ES is the average loss in the worst (1-confidence)% of cases
    tail_returns = sorted_returns[:var_index] if var_index > 0 else sorted_returns[:1]
    
    if tail_returns:
        expected_shortfall = float(abs(np.mean(tail_returns)) * 100)  # Ensure Python float
    else:
        # Fallback if no tail returns
        expected_shortfall = float(var_95 * 1.3)  # ES typically ~30% higher than VaR
    
    # Add final metadata
    data_quality_metadata["var_95"] = round(var_95, 4)
    data_quality_metadata["expected_shortfall"] = round(expected_shortfall, 4)
    data_quality_metadata["var_method"] = "historical_simulation"
    
    logger.info(
        f"VaR calculation complete: {len(portfolio_returns)} daily returns analyzed, "
        f"VaR(95%)={var_95:.2f}%, ES={expected_shortfall:.2f}%, "
        f"Quality: {data_quality_metadata['overall_quality']}"
    )
    
    return var_95, expected_shortfall, data_quality_metadata


def _calculate_top_event_risks(
    positions: List[PortfolioPosition],
    upcoming_events: List[Event],
    total_value: float,
    db: Session,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Identify top N event risks by dollar exposure.
    
    Returns:
        List[Dict]: Top event risks sorted by dollar exposure
    """
    event_risks = []
    
    for event in upcoming_events:
        # Find position for this event's ticker
        position = next(
            (p for p in positions if p.ticker == event.ticker), 
            None
        )
        
        if not position:
            continue
        
        # Calculate exposure
        position_value = position.qty * position.avg_price
        position_size_pct = (position_value / total_value) * 100
        
        # Estimate impact % from event score
        event_score = event.ml_adjusted_score if event.ml_adjusted_score else event.impact_score
        
        if event_score >= 80:
            estimated_impact_pct = 5.0 + (event_score - 80) * 0.25
        elif event_score >= 50:
            estimated_impact_pct = 2.0 + (event_score - 50) * 0.1
        else:
            estimated_impact_pct = 0.5 + (event_score / 50) * 1.5
        
        dollar_exposure = position_value * (estimated_impact_pct / 100)
        
        event_risks.append({
            "event_id": event.id,
            "ticker": event.ticker,
            "event_type": event.event_type,
            "title": event.title,
            "date": event.date.isoformat(),
            "impact_score": event_score,
            "direction": event.direction,
            "position_size_pct": round(position_size_pct, 2),
            "estimated_impact_pct": round(estimated_impact_pct, 2),
            "dollar_exposure": round(dollar_exposure, 2)
        })
    
    # Sort by dollar exposure (descending) and take top N
    event_risks.sort(key=lambda x: abs(x["dollar_exposure"]), reverse=True)
    
    return event_risks[:top_n]


def _generate_hedge_recommendation(
    position: PortfolioPosition,
    event: Event,
    position_size_pct: float,
    estimated_impact_pct: float,
    dollar_exposure: float
) -> Optional[str]:
    """
    Generate hedge recommendation based on exposure metrics.
    
    Returns:
        Optional[str]: Hedge recommendation or None if hedging not recommended
    """
    # Only recommend hedging for significant exposures
    # High risk: >5% position size AND >3% estimated impact
    # Medium risk: >10% position size AND >2% estimated impact
    
    abs_impact = abs(estimated_impact_pct)
    
    if position_size_pct > 5 and abs_impact > 3:
        # High risk scenario
        if event.direction and event.direction.lower() == "negative":
            return (
                f"HIGH RISK: Consider buying protective puts on {position.ticker}. "
                f"Estimated downside exposure: ${dollar_exposure:.2f}. "
                f"Alternative: Reduce position size by 25-50% before {event.event_type}."
            )
        elif event.direction and event.direction.lower() == "positive":
            return (
                f"UPSIDE OPPORTUNITY: Consider selling covered calls on {position.ticker} "
                f"to capture premium before {event.event_type}. "
                f"Estimated upside potential: ${dollar_exposure:.2f}."
            )
        else:
            return (
                f"ELEVATED RISK: Consider straddle/strangle strategy on {position.ticker}. "
                f"Event volatility exposure: ${dollar_exposure:.2f}. "
                f"Direction uncertain - prepare for significant move."
            )
    
    elif position_size_pct > 10 and abs_impact > 2:
        # Medium risk - concentrated position
        return (
            f"MODERATE RISK: Position represents {position_size_pct:.1f}% of portfolio. "
            f"Consider reducing position by 20-30% or using collar strategy "
            f"(protective put + covered call) to limit downside while capping upside."
        )
    
    return None  # No hedge recommended for low-risk exposures
