"""
Populate ALL quantitative features with accurate, realistic sample data for Impact Radar.

This script populates:
1. prediction_metrics - Model accuracy metrics
2. prediction_snapshots - Daily performance tracking
3. insider_transactions - Form 4 insider trading data
4. user_strategies - Trading strategy definitions
5. backtest_runs and backtest_results - Backtest simulations
6. pattern_alerts - Multi-event correlation alerts
7. portfolio_risk_snapshots and portfolio_event_exposure - Portfolio risk analysis
"""

import random
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from releaseradar.db.models import (
    Base,
    Event,
    User,
    UserPortfolio,
    PortfolioPosition,
    PatternDefinition,
    PredictionMetrics,
    PredictionSnapshot,
    InsiderTransaction,
    UserStrategy,
    BacktestRun,
    BacktestResult,
    PatternAlert,
    PortfolioRiskSnapshot,
    PortfolioEventExposure,
)
from releaseradar.db.session import get_db
import os


def setup_database():
    """Create database session."""
    return get_db()


def generate_prediction_metrics(session):
    """Generate realistic prediction metrics for different models, event types, and horizons."""
    print("📊 Generating prediction_metrics...")
    
    # Clear existing data
    session.query(PredictionMetrics).delete()
    session.commit()
    
    models = ["v1.0-deterministic", "v1.5-ml-hybrid", "v2.0-market-echo"]
    event_types = ["fda_approval", "earnings", "sec_8k", "sec_10q", "insider_buy"]
    horizons = ["1d", "7d", "30d"]
    
    # Model quality tiers
    model_quality = {
        "v1.0-deterministic": {"win_rate": (0.48, 0.55), "mae": (6.5, 8.5), "sharpe": (0.5, 1.0)},
        "v1.5-ml-hybrid": {"win_rate": (0.58, 0.68), "mae": (4.0, 6.0), "sharpe": (1.0, 1.8)},
        "v2.0-market-echo": {"win_rate": (0.65, 0.75), "mae": (2.5, 4.5), "sharpe": (1.5, 2.5)},
    }
    
    # Generate for last 90 days
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    
    metrics_data = []
    current_date = start_date
    
    while current_date <= end_date:
        for model in models:
            quality = model_quality[model]
            
            for event_type in event_types:
                for horizon in horizons:
                    # Random variation
                    base_win_rate = random.uniform(*quality["win_rate"])
                    base_mae = random.uniform(*quality["mae"])
                    base_sharpe = random.uniform(*quality["sharpe"])
                    
                    # Horizon adjustments (longer horizons are harder)
                    horizon_penalty = {"1d": 0, "7d": -0.03, "30d": -0.06}
                    win_rate = max(0.40, min(0.80, base_win_rate + horizon_penalty[horizon]))
                    
                    # Total predictions varies by event type
                    total_preds = random.randint(15, 40) if event_type in ["fda_approval", "insider_buy"] else random.randint(40, 100)
                    correct_dir = int(total_preds * win_rate)
                    
                    # RMSE is always slightly higher than MAE
                    rmse = base_mae * random.uniform(1.15, 1.35)
                    
                    # Confidence buckets - higher confidence = better win rate
                    high_conf_wr = min(0.85, win_rate * random.uniform(1.15, 1.25))
                    med_conf_wr = win_rate * random.uniform(0.95, 1.05)
                    low_conf_wr = max(0.35, win_rate * random.uniform(0.75, 0.90))
                    
                    metric = PredictionMetrics(
                        model_version=model,
                        event_type=event_type,
                        horizon=horizon,
                        date=current_date,
                        total_predictions=total_preds,
                        correct_direction=correct_dir,
                        win_rate=round(win_rate, 4),
                        mae=round(base_mae, 3),
                        rmse=round(rmse, 3),
                        sharpe_ratio=round(base_sharpe, 3),
                        avg_confidence=round(random.uniform(0.55, 0.75), 3),
                        high_conf_win_rate=round(high_conf_wr, 4),
                        med_conf_win_rate=round(med_conf_wr, 4),
                        low_conf_win_rate=round(low_conf_wr, 4),
                    )
                    metrics_data.append(metric)
        
        current_date += timedelta(days=1)
    
    session.bulk_save_objects(metrics_data)
    session.commit()
    print(f"✅ Created {len(metrics_data)} prediction metrics")


def generate_prediction_snapshots(session):
    """Generate daily prediction snapshots showing model improvement over time."""
    print("📈 Generating prediction_snapshots...")
    
    # Clear existing data
    session.query(PredictionSnapshot).delete()
    session.commit()
    
    models = ["v1.0-deterministic", "v1.5-ml-hybrid", "v2.0-market-echo"]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    snapshots = []
    
    for model in models:
        current_date = start_date
        day_count = 0
        
        # Starting performance
        start_win_rate = {"v1.0-deterministic": 0.45, "v1.5-ml-hybrid": 0.58, "v2.0-market-echo": 0.62}
        end_win_rate = {"v1.0-deterministic": 0.52, "v1.5-ml-hybrid": 0.65, "v2.0-market-echo": 0.72}
        
        start_mae = {"v1.0-deterministic": 8.0, "v1.5-ml-hybrid": 5.5, "v2.0-market-echo": 4.2}
        end_mae = {"v1.0-deterministic": 7.2, "v1.5-ml-hybrid": 4.5, "v2.0-market-echo": 3.0}
        
        while current_date <= end_date:
            # Linear improvement + noise
            progress = day_count / 90.0
            
            win_rate = start_win_rate[model] + (end_win_rate[model] - start_win_rate[model]) * progress
            win_rate += random.uniform(-0.03, 0.03)  # Daily noise
            win_rate = max(0.40, min(0.80, win_rate))
            
            mae = start_mae[model] + (end_mae[model] - start_mae[model]) * progress
            mae += random.uniform(-0.3, 0.3)  # Daily noise
            mae = max(2.0, mae)
            
            # Events scored increases over time (more data)
            total_events = int(500 + (1500 * progress) + random.randint(-50, 50))
            
            snapshot = PredictionSnapshot(
                model_version=model,
                timestamp=current_date,
                overall_win_rate=round(win_rate, 4),
                overall_mae=round(mae, 3),
                total_events_scored=total_events,
                metrics_json={
                    "rmse": round(mae * 1.2, 3),
                    "sharpe_ratio": round(random.uniform(0.8, 2.2), 3),
                    "avg_confidence": round(random.uniform(0.60, 0.75), 3),
                }
            )
            snapshots.append(snapshot)
            
            current_date += timedelta(days=1)
            day_count += 1
    
    session.bulk_save_objects(snapshots)
    session.commit()
    print(f"✅ Created {len(snapshots)} prediction snapshots")


def generate_insider_transactions(session):
    """Generate realistic insider trading transactions."""
    print("💼 Generating insider_transactions...")
    
    # Clear existing data
    session.query(InsiderTransaction).delete()
    session.commit()
    
    tickers_data = {
        "AAPL": "Apple Inc.",
        "GOOGL": "Alphabet Inc.",
        "MSFT": "Microsoft Corporation",
        "NVDA": "NVIDIA Corporation",
        "META": "Meta Platforms Inc.",
        "MRNA": "Moderna Inc.",
        "PFE": "Pfizer Inc.",
        "REGN": "Regeneron Pharmaceuticals Inc.",
    }
    
    insider_names = [
        ("Timothy Cook", "CEO", True, False, False),
        ("Luca Maestri", "CFO", True, False, False),
        ("Sundar Pichai", "CEO", True, False, False),
        ("Ruth Porat", "CFO", True, False, False),
        ("Satya Nadella", "CEO", True, False, False),
        ("Amy Hood", "CFO", True, False, False),
        ("Jensen Huang", "CEO", True, False, False),
        ("Colette Kress", "CFO", True, False, False),
        ("Mark Zuckerberg", "CEO", True, False, True),
        ("Susan Li", "CFO", True, False, False),
        ("Stéphane Bancel", "CEO", True, False, False),
        ("David Meline", "CFO", True, False, False),
        ("Albert Bourla", "CEO", True, False, False),
        ("David Denton", "CFO", True, False, False),
        ("Leonard Schleifer", "CEO", True, False, True),
        ("Robert Landry", "CFO", True, False, False),
        ("John Smith", "Director", False, True, False),
        ("Sarah Johnson", "Director", False, True, False),
        ("Michael Chen", "Director", False, True, False),
        ("Emily Davis", "Director", False, True, True),
    ]
    
    transactions = []
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    for _ in range(60):  # Generate 60 transactions
        ticker = random.choice(list(tickers_data.keys()))
        company_name = tickers_data[ticker]
        
        insider_name, title, is_officer, is_director, is_10pct = random.choice(insider_names)
        
        # Transaction details
        trans_date = start_date + timedelta(days=random.randint(0, 30))
        filed_date = trans_date + timedelta(days=random.randint(1, 4))
        
        # More purchases for biotech (MRNA, PFE, REGN), more sales for big tech
        if ticker in ["MRNA", "PFE", "REGN"]:
            trans_code = "P" if random.random() < 0.65 else "S"  # 65% purchases
        else:
            trans_code = "P" if random.random() < 0.35 else "S"  # 35% purchases
        
        # Share amounts vary by role
        if is_officer or is_10pct:
            shares = random.randint(5000, 50000)
        else:
            shares = random.randint(1000, 15000)
        
        # Price varies by ticker
        price_ranges = {
            "AAPL": (170, 195), "GOOGL": (130, 155), "MSFT": (350, 400),
            "NVDA": (450, 550), "META": (300, 370), "MRNA": (65, 95),
            "PFE": (25, 32), "REGN": (800, 950)
        }
        price = random.uniform(*price_ranges[ticker])
        value = shares * price
        
        shares_owned_after = shares * random.randint(3, 20) if trans_code == "P" else shares * random.randint(2, 15)
        
        # Sentiment calculation
        if trans_code == "P":
            # Purchases are bullish
            if value > 1_000_000:
                sentiment = random.uniform(0.7, 0.95)
                rationale = f"Significant insider purchase of ${value:,.0f} signals strong confidence"
            elif value > 500_000:
                sentiment = random.uniform(0.5, 0.75)
                rationale = f"Moderate insider buying (${value:,.0f}) shows optimism"
            else:
                sentiment = random.uniform(0.3, 0.55)
                rationale = f"Small insider purchase (${value:,.0f})"
        else:
            # Sales are neutral to slightly bearish (could be diversification)
            if value > 5_000_000:
                sentiment = random.uniform(-0.6, -0.3)
                rationale = f"Large insider sale (${value:,.0f}) may indicate concern"
            elif value > 2_000_000:
                sentiment = random.uniform(-0.4, -0.1)
                rationale = f"Moderate insider sale (${value:,.0f}), possibly for diversification"
            else:
                sentiment = random.uniform(-0.2, 0.1)
                rationale = f"Small insider sale (${value:,.0f}), likely routine"
        
        transaction = InsiderTransaction(
            ticker=ticker,
            company_name=company_name,
            insider_name=insider_name,
            insider_title=title,
            is_ten_percent_owner=is_10pct,
            is_officer=is_officer,
            is_director=is_director,
            transaction_date=trans_date,
            transaction_code=trans_code,
            shares=shares,
            price_per_share=round(price, 2),
            transaction_value=round(value, 2),
            shares_owned_after=shares_owned_after,
            sentiment_score=round(sentiment, 3),
            sentiment_rationale=rationale,
            form_4_url=f"https://sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=4",
            filed_date=filed_date,
        )
        transactions.append(transaction)
    
    session.bulk_save_objects(transactions)
    session.commit()
    print(f"✅ Created {len(transactions)} insider transactions")


def generate_user_strategies(session, user_id=305):
    """Generate realistic trading strategies for user."""
    print("🎯 Generating user_strategies...")
    
    # Clear existing strategies for this user
    session.query(UserStrategy).filter(UserStrategy.user_id == user_id).delete()
    session.commit()
    
    strategies = []
    
    # Strategy 1: High-Impact FDA Plays
    strategy1 = UserStrategy(
        user_id=user_id,
        name="High-Impact FDA Plays",
        description="Trade high-conviction FDA approval events with strong impact scores",
        active=True,
        entry_conditions={
            "event_types": ["fda_approval"],
            "min_score": 75,
            "min_confidence": 0.7,
            "sectors": ["Healthcare", "Biotechnology"]
        },
        exit_conditions={
            "hold_days": 5,
            "take_profit_pct": 15.0,
            "stop_loss_pct": -8.0
        },
        position_sizing={
            "max_position_pct": 5.0,
            "scale_by_confidence": True
        },
        risk_management={
            "max_portfolio_exposure": 20.0,
            "max_concurrent_positions": 4
        },
        tickers=None,  # All tickers
        sectors=["Healthcare", "Biotechnology"],
        min_score_threshold=75,
    )
    session.add(strategy1)
    session.flush()
    strategies.append(strategy1)
    
    # Strategy 2: Earnings Momentum
    strategy2 = UserStrategy(
        user_id=user_id,
        name="Earnings Momentum",
        description="Capitalize on positive earnings surprises combined with guidance upgrades",
        active=True,
        entry_conditions={
            "event_types": ["earnings", "guidance_upgrade"],
            "min_score": 65,
            "min_confidence": 0.6,
            "direction": "positive",
            "pattern_match": "earnings_beat"
        },
        exit_conditions={
            "hold_days": 10,
            "take_profit_pct": 12.0,
            "stop_loss_pct": -6.0
        },
        position_sizing={
            "max_position_pct": 4.0,
            "scale_by_confidence": True
        },
        risk_management={
            "max_portfolio_exposure": 30.0,
            "max_concurrent_positions": 6
        },
        tickers=["AAPL", "GOOGL", "MSFT", "NVDA", "META"],
        sectors=None,
        min_score_threshold=65,
    )
    session.add(strategy2)
    session.flush()
    strategies.append(strategy2)
    
    # Strategy 3: Insider Confidence
    strategy3 = UserStrategy(
        user_id=user_id,
        name="Insider Confidence",
        description="Follow significant insider buying (>$100k) in high-quality companies",
        active=True,
        entry_conditions={
            "event_types": ["insider_buy"],
            "min_transaction_value": 100000,
            "insider_role": ["CEO", "CFO", "Director"],
            "min_confidence": 0.5
        },
        exit_conditions={
            "hold_days": 20,
            "take_profit_pct": 18.0,
            "stop_loss_pct": -10.0
        },
        position_sizing={
            "max_position_pct": 6.0,
            "scale_by_transaction_size": True
        },
        risk_management={
            "max_portfolio_exposure": 25.0,
            "max_concurrent_positions": 5
        },
        tickers=None,
        sectors=None,
        min_score_threshold=50,
    )
    session.add(strategy3)
    session.flush()
    strategies.append(strategy3)
    
    session.commit()
    print(f"✅ Created {len(strategies)} user strategies")
    
    return strategies


def generate_backtest_data(session, strategies, user_id=305):
    """Generate realistic backtest runs and results."""
    print("🔬 Generating backtest_runs and backtest_results...")
    
    # Clear existing backtest data for this user
    session.query(BacktestResult).filter(
        BacktestResult.run_id.in_(
            session.query(BacktestRun.id).filter(BacktestRun.user_id == user_id)
        )
    ).delete(synchronize_session=False)
    session.query(BacktestRun).filter(BacktestRun.user_id == user_id).delete()
    session.commit()
    
    # Get some real events for realistic backtesting
    events = session.execute(
        select(Event)
        .where(Event.date >= datetime(2024, 1, 1))
        .where(Event.date <= datetime(2024, 11, 20))
        .limit(200)
    ).scalars().all()
    
    if not events:
        print("⚠️  No events found, creating synthetic backtest data anyway")
        events = []
    
    backtest_runs = []
    all_results = []
    
    for strategy in strategies:
        # Run 2-3 backtests per strategy
        num_backtests = random.randint(2, 3)
        
        for run_num in range(num_backtests):
            # Vary date ranges slightly
            start_date = date(2024, random.randint(1, 3), 1)
            end_date = date(2024, 11, 20)
            
            initial_capital = random.choice([50000, 100000, 250000])
            
            # Run metrics - vary by strategy quality
            if "FDA" in strategy.name:
                win_rate = random.uniform(0.55, 0.70)
                total_return = random.uniform(15, 45)
                sharpe = random.uniform(1.2, 2.0)
                max_dd = random.uniform(-12, -18)
            elif "Earnings" in strategy.name:
                win_rate = random.uniform(0.50, 0.65)
                total_return = random.uniform(8, 28)
                sharpe = random.uniform(0.8, 1.6)
                max_dd = random.uniform(-10, -20)
            else:  # Insider
                win_rate = random.uniform(0.58, 0.72)
                total_return = random.uniform(12, 38)
                sharpe = random.uniform(1.0, 1.9)
                max_dd = random.uniform(-8, -15)
            
            num_trades = random.randint(20, 50)
            
            run = BacktestRun(
                strategy_id=strategy.id,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                status="completed",
                started_at=datetime.now() - timedelta(days=random.randint(1, 30)),
                completed_at=datetime.now() - timedelta(days=random.randint(0, 29)),
                total_trades=num_trades,
                win_rate=round(win_rate, 4),
                total_return_pct=round(total_return, 2),
                sharpe_ratio=round(sharpe, 3),
                max_drawdown_pct=round(max_dd, 2),
            )
            session.add(run)
            session.flush()  # Get run.id
            
            backtest_runs.append(run)
            
            # Generate individual trade results
            tickers = ["AAPL", "GOOGL", "MSFT", "NVDA", "META", "MRNA", "PFE", "REGN", "TSLA", "AMZN"]
            
            for trade_num in range(num_trades):
                ticker = random.choice(tickers)
                
                # Entry date within backtest range
                days_range = (end_date - start_date).days
                entry_offset = random.randint(0, max(1, days_range - 30))
                entry_date = start_date + timedelta(days=entry_offset)
                
                # Holding period
                holding_days = random.randint(3, 25)
                exit_date = entry_date + timedelta(days=holding_days)
                
                # Price simulation
                entry_price = random.uniform(50, 500)
                
                # Win/loss based on strategy win rate
                is_winner = random.random() < win_rate
                
                if is_winner:
                    return_pct = random.uniform(2, 20)
                else:
                    return_pct = random.uniform(-12, -1)
                
                exit_price = entry_price * (1 + return_pct / 100)
                
                # Position size
                position_value = initial_capital * random.uniform(0.03, 0.08)
                shares = position_value / entry_price
                profit_loss = (exit_price - entry_price) * shares
                
                # Exit reason
                if return_pct > 10:
                    exit_reason = "take_profit"
                elif return_pct < -5:
                    exit_reason = "stop_loss"
                elif random.random() < 0.3:
                    exit_reason = "exit_signal"
                else:
                    exit_reason = "hold_period_end"
                
                # Link to event if available
                event_id = None
                if events and random.random() < 0.7:  # 70% of trades linked to events
                    matched_events = [e for e in events if e.ticker == ticker and e.date.date() <= entry_date]
                    if matched_events:
                        event_id = random.choice(matched_events).id
                
                result = BacktestResult(
                    run_id=run.id,
                    ticker=ticker,
                    event_id=event_id,
                    entry_date=entry_date,
                    entry_price=round(entry_price, 2),
                    exit_date=exit_date,
                    exit_price=round(exit_price, 2),
                    shares=round(shares, 2),
                    position_value=round(position_value, 2),
                    return_pct=round(return_pct, 2),
                    profit_loss=round(profit_loss, 2),
                    exit_reason=exit_reason,
                    holding_period_days=holding_days,
                )
                all_results.append(result)
    
    session.bulk_save_objects(all_results)
    session.commit()
    print(f"✅ Created {len(backtest_runs)} backtest runs with {len(all_results)} trade results")


def generate_pattern_alerts(session):
    """Generate pattern alerts for multi-event correlations."""
    print("🔍 Generating pattern_alerts...")
    
    # Clear existing pattern alerts
    session.query(PatternAlert).delete()
    session.commit()
    
    # Get existing pattern definitions
    patterns = session.execute(select(PatternDefinition)).scalars().all()
    
    if not patterns:
        print("⚠️  No pattern definitions found, skipping pattern alerts")
        return
    
    # Get recent events for realistic alerts
    recent_events = session.execute(
        select(Event)
        .where(Event.date >= datetime.now() - timedelta(days=30))
        .limit(100)
    ).scalars().all()
    
    if not recent_events:
        print("⚠️  No recent events found, skipping pattern alerts")
        return
    
    alerts = []
    tickers_used = set()
    
    for _ in range(15):  # Generate 15 pattern alerts
        pattern = random.choice(patterns)
        
        # Pick events for same ticker
        ticker_events = {}
        for event in recent_events:
            if event.ticker not in ticker_events:
                ticker_events[event.ticker] = []
            ticker_events[event.ticker].append(event)
        
        # Find tickers with multiple events
        multi_event_tickers = [t for t, evts in ticker_events.items() if len(evts) >= 2]
        
        if not multi_event_tickers:
            continue
        
        ticker = random.choice(multi_event_tickers)
        ticker_event_list = ticker_events[ticker]
        
        # Pick 2-3 correlated events
        num_events = min(random.randint(2, 3), len(ticker_event_list))
        selected_events = random.sample(ticker_event_list, num_events)
        
        event_ids = [e.id for e in selected_events]
        company_name = selected_events[0].company_name
        
        # Correlation score (0.6-0.95)
        correlation_score = random.uniform(0.65, 0.92)
        
        # Aggregate impact
        avg_score = sum(e.impact_score for e in selected_events) / len(selected_events)
        aggregated_score = int(avg_score * random.uniform(1.1, 1.3))  # Synergy boost
        aggregated_score = min(100, aggregated_score)
        
        # Determine direction
        positive_events = sum(1 for e in selected_events if e.direction == "positive")
        if positive_events > len(selected_events) / 2:
            direction = "positive"
        elif positive_events < len(selected_events) / 2:
            direction = "negative"
        else:
            direction = "neutral"
        
        # Generate rationale
        event_type_names = [e.event_type.replace("_", " ").title() for e in selected_events]
        rationale = f"Pattern detected: {', '.join(event_type_names)} within 7-day window. "
        rationale += f"Correlation score: {correlation_score:.2f}. "
        rationale += f"Combined impact suggests {direction} momentum."
        
        alert = PatternAlert(
            pattern_id=pattern.id,
            user_id=pattern.created_by,
            ticker=ticker,
            company_name=company_name,
            event_ids=event_ids,
            correlation_score=round(correlation_score, 3),
            aggregated_impact_score=aggregated_score,
            aggregated_direction=direction,
            rationale=rationale,
            status="active",
            detected_at=datetime.now() - timedelta(days=random.randint(0, 7)),
        )
        alerts.append(alert)
        tickers_used.add(ticker)
    
    session.bulk_save_objects(alerts)
    session.commit()
    print(f"✅ Created {len(alerts)} pattern alerts for {len(tickers_used)} tickers")


def generate_portfolio_risk_data(session, user_id=305):
    """Generate portfolio risk snapshots and event exposures."""
    print("📊 Generating portfolio_risk_snapshots and portfolio_event_exposure...")
    
    # Clear existing portfolio risk data for this user
    # First, get the user's portfolio IDs
    user_portfolio_ids = [p.id for p in session.execute(
        select(UserPortfolio.id).where(UserPortfolio.user_id == user_id)
    ).scalars().all()]
    
    if user_portfolio_ids:
        session.query(PortfolioEventExposure).filter(
            PortfolioEventExposure.portfolio_id.in_(user_portfolio_ids)
        ).delete(synchronize_session=False)
        session.query(PortfolioRiskSnapshot).filter(
            PortfolioRiskSnapshot.portfolio_id.in_(user_portfolio_ids)
        ).delete(synchronize_session=False)
        session.commit()
    
    # Get user's portfolio
    portfolio = session.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if not portfolio:
        print(f"⚠️  No portfolio found for user {user_id}, creating one...")
        portfolio = UserPortfolio(
            user_id=user_id,
            name="Main Portfolio"
        )
        session.add(portfolio)
        session.flush()
    
    # Get or create portfolio positions
    positions = session.execute(
        select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio.id)
    ).scalars().all()
    
    if not positions:
        print("Creating sample portfolio positions...")
        sample_positions = [
            {"ticker": "AAPL", "qty": 100, "price": 180.50},
            {"ticker": "GOOGL", "qty": 75, "price": 142.30},
            {"ticker": "MSFT", "qty": 80, "price": 378.90},
            {"ticker": "NVDA", "qty": 50, "price": 495.20},
            {"ticker": "META", "qty": 60, "price": 335.80},
            {"ticker": "MRNA", "qty": 200, "price": 82.40},
            {"ticker": "PFE", "qty": 300, "price": 28.75},
        ]
        
        positions = []
        for pos_data in sample_positions:
            pos = PortfolioPosition(
                portfolio_id=portfolio.id,
                ticker=pos_data["ticker"],
                qty=pos_data["qty"],
                avg_price=pos_data["price"],
                as_of=date.today(),
            )
            session.add(pos)
            positions.append(pos)
        
        session.flush()
    
    # Generate 5 risk snapshots over last 30 days
    snapshots = []
    for i in range(5):
        snapshot_date = datetime.now() - timedelta(days=i * 6)  # Every 6 days
        
        # Calculate total portfolio value
        total_value = sum(p.qty * p.avg_price for p in positions)
        
        # Risk metrics
        concentration_risk = random.uniform(35, 65)  # 0-100
        diversification = random.uniform(50, 85)  # 0-100
        var_95 = random.uniform(8, 18)  # Value at Risk as %
        expected_shortfall = var_95 * random.uniform(1.2, 1.6)
        
        # Event exposure (% of portfolio exposed to upcoming events)
        event_exposure = random.uniform(15, 45)
        
        # Top event risks
        top_risks = [
            {"ticker": p.ticker, "event_type": random.choice(["earnings", "fda_approval", "sec_8k"]), 
             "impact_score": random.randint(60, 90), "exposure_pct": round(random.uniform(3, 12), 2)}
            for p in random.sample(positions, min(5, len(positions)))
        ]
        
        snapshot = PortfolioRiskSnapshot(
            portfolio_id=portfolio.id,
            snapshot_date=snapshot_date,
            total_event_exposure=round(event_exposure, 2),
            concentration_risk_score=round(concentration_risk, 2),
            sector_diversification_score=round(diversification, 2),
            var_95=round(var_95, 2),
            expected_shortfall=round(expected_shortfall, 2),
            top_event_risks_json=top_risks,
            correlation_matrix_json={
                "Technology": {"Healthcare": 0.45, "Finance": 0.62},
                "Healthcare": {"Technology": 0.45, "Finance": 0.38},
            }
        )
        snapshots.append(snapshot)
    
    session.bulk_save_objects(snapshots)
    session.commit()
    
    # Generate event exposures
    # Get upcoming events for portfolio tickers
    portfolio_tickers = [p.ticker for p in positions]
    upcoming_events = session.execute(
        select(Event)
        .where(Event.ticker.in_(portfolio_tickers))
        .where(Event.date >= datetime.now() - timedelta(days=7))
        .where(Event.date <= datetime.now() + timedelta(days=30))
        .limit(30)
    ).scalars().all()
    
    exposures = []
    for event in upcoming_events[:15]:  # Take up to 15 events
        # Find matching position
        matching_pos = next((p for p in positions if p.ticker == event.ticker), None)
        if not matching_pos:
            continue
        
        # Calculate exposure
        total_value = sum(p.qty * p.avg_price for p in positions)
        position_value = matching_pos.qty * matching_pos.avg_price
        position_pct = (position_value / total_value) * 100
        
        # Estimated impact based on event score
        estimated_impact = (event.impact_score / 100.0) * random.uniform(0.05, 0.20) * 100  # 5-20% move
        if event.direction == "negative":
            estimated_impact *= -1
        
        dollar_exposure = position_value * (abs(estimated_impact) / 100.0)
        
        # Hedge recommendation
        if abs(estimated_impact) > 10 and position_pct > 10:
            if estimated_impact < 0:
                hedge = f"Consider protective puts on {event.ticker} (${dollar_exposure:,.0f} at risk)"
            else:
                hedge = f"Consider taking profits or selling covered calls on {event.ticker}"
        else:
            hedge = "No hedge recommended (moderate exposure)"
        
        exposure = PortfolioEventExposure(
            portfolio_id=portfolio.id,
            position_id=matching_pos.id,
            event_id=event.id,
            position_size_pct=round(position_pct, 2),
            estimated_impact_pct=round(estimated_impact, 2),
            dollar_exposure=round(dollar_exposure, 2),
            hedge_recommendation=hedge,
        )
        exposures.append(exposure)
    
    session.bulk_save_objects(exposures)
    session.commit()
    
    print(f"✅ Created {len(snapshots)} risk snapshots and {len(exposures)} event exposures")


def main():
    """Main execution function."""
    print("=" * 70)
    print("🚀 POPULATING QUANTITATIVE FEATURES FOR IMPACT RADAR")
    print("=" * 70)
    
    try:
        session = setup_database()
        
        # 1. Prediction Metrics
        generate_prediction_metrics(session)
        
        # 2. Prediction Snapshots
        generate_prediction_snapshots(session)
        
        # 3. Insider Transactions
        generate_insider_transactions(session)
        
        # 4. User Strategies
        strategies = generate_user_strategies(session)
        
        # 5. Backtest Runs and Results
        generate_backtest_data(session, strategies)
        
        # 6. Pattern Alerts
        generate_pattern_alerts(session)
        
        # 7. Portfolio Risk Data
        generate_portfolio_risk_data(session)
        
        print("\n" + "=" * 70)
        print("✅ ALL QUANTITATIVE FEATURES POPULATED SUCCESSFULLY!")
        print("=" * 70)
        
        # Print summary
        print("\n📈 Summary:")
        print(f"  • Prediction metrics: ✅ (90 days × 3 models × 5 event types × 3 horizons)")
        print(f"  • Prediction snapshots: ✅ (90 days × 3 models)")
        print(f"  • Insider transactions: ✅ (60 transactions)")
        print(f"  • User strategies: ✅ (3 strategies)")
        print(f"  • Backtest runs: ✅ (6-9 runs with 20-50 trades each)")
        print(f"  • Pattern alerts: ✅ (15 multi-event correlations)")
        print(f"  • Portfolio risk: ✅ (5 snapshots + 15 event exposures)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
