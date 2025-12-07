import streamlit as st
from data_manager import DataManager
from scanner_service import get_scanner_service
from payment_service import get_payment_service
from auth_service import AuthService
from email_service import EmailService
from sms_service import SMSService
import yfinance as yf
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Impact Radar",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_phone' not in st.session_state:
    st.session_state.user_phone = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'login'
if 'pending_user_id' not in st.session_state:
    st.session_state.pending_user_id = None
if 'verification_method' not in st.session_state:
    st.session_state.verification_method = None

def user_is_admin():
    """Check if current user has admin privileges."""
    return st.session_state.get('is_admin', False)

data_manager = DataManager()
scanner_service = get_scanner_service()
payment_service = get_payment_service()

def show_auth_pages():
    """Display authentication pages (login, signup, verification)."""
    st.markdown("### Impact Radar")
    st.caption("Market-moving events, tracked to the second.")
    st.markdown("---")
    
    if st.session_state.auth_page == 'login':
        show_login_page()
    elif st.session_state.auth_page == 'signup':
        show_signup_page()
    elif st.session_state.auth_page == 'verify':
        show_verification_page()

def show_login_page():
    """Display login page."""
    st.markdown("## Login to Your Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form", clear_on_submit=False):
            login_method = st.radio("Login with:", ["Email", "Phone"], horizontal=True)
            
            if login_method == "Email":
                identifier = st.text_input("Email Address", placeholder="you@example.com")
                use_email = True
            else:
                identifier = st.text_input("Phone Number", placeholder="+1234567890")
                use_email = False
            
            password = st.text_input("Password", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                login_submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            
            with col_btn2:
                create_account_submitted = st.form_submit_button("Create Account", use_container_width=True)
        
        if login_submitted:
            if not identifier or not password:
                st.error("Please fill in all fields")
            else:
                if use_email:
                    result = AuthService.login(email=identifier, password=password)
                else:
                    result = AuthService.login(phone=identifier, password=password)
                
                if result['success']:
                    st.session_state.authenticated = True
                    st.session_state.user_id = result['user_id']
                    st.session_state.user_email = result.get('email')
                    st.session_state.user_phone = result.get('phone')
                    st.session_state.is_admin = result.get('is_admin', False)
                    st.success("Login successful!")
                    st.rerun()
                elif 'user_id' in result:
                    user = AuthService.get_user(result['user_id'])
                    st.session_state.pending_user_id = result['user_id']
                    st.session_state.verification_method = user['verification_method']
                    st.session_state.auth_page = 'verify'
                    st.warning("Account not verified. Please verify your account.")
                    st.rerun()
                else:
                    st.error(result.get('error', 'Login failed'))
        
        if create_account_submitted:
            st.session_state.auth_page = 'signup'
            st.rerun()

def show_signup_page():
    """Display signup page."""
    st.markdown("## Create Your Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("signup_form", clear_on_submit=False):
            signup_method = st.radio("Sign up with:", ["Email", "Phone"], horizontal=True)
            
            if signup_method == "Email":
                identifier = st.text_input("Email Address", placeholder="you@example.com")
                use_email = True
                method = "email"
            else:
                identifier = st.text_input("Phone Number", placeholder="+1234567890")
                use_email = False
                method = "phone"
            
            password = st.text_input("Password", type="password", help="Minimum 6 characters")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                signup_submitted = st.form_submit_button("Sign Up", type="primary", use_container_width=True)
            
            with col_btn2:
                back_submitted = st.form_submit_button("Back to Login", use_container_width=True)
        
        if signup_submitted:
            if not identifier or not password or not confirm_password:
                st.error("Please fill in all fields")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                if use_email:
                    result = AuthService.create_user(email=identifier, password=password, verification_method=method)
                else:
                    result = AuthService.create_user(phone=identifier, password=password, verification_method=method)
                
                if result['success']:
                    user_id = result['user_id']
                    code_result = AuthService.create_verification_code(user_id, method)
                    
                    if code_result['success']:
                        if use_email:
                            email_result = EmailService.send_verification_code(identifier, code_result['code'])
                            if email_result['success']:
                                st.session_state.pending_user_id = user_id
                                st.session_state.verification_method = method
                                st.session_state.auth_page = 'verify'
                                st.success("Account created! Check your email for verification code.")
                                st.rerun()
                            else:
                                st.error(f"Failed to send email: {email_result.get('error', 'Unknown error')}")
                        else:
                            sms_result = SMSService.send_verification_code(identifier, code_result['code'])
                            if sms_result['success']:
                                st.session_state.pending_user_id = user_id
                                st.session_state.verification_method = method
                                st.session_state.auth_page = 'verify'
                                st.success("Account created! Check your phone for verification code.")
                                st.rerun()
                            else:
                                st.error(f"Failed to send SMS: {sms_result.get('error', 'Unknown error')}")
                    else:
                        st.error("Failed to create verification code")
                else:
                    st.error(result.get('error', 'Signup failed'))
        
        if back_submitted:
            st.session_state.auth_page = 'login'
            st.rerun()

def show_verification_page():
    """Display verification page."""
    st.markdown("## Verify Your Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info(f"A verification code has been sent to your {st.session_state.verification_method}. Please enter it below.")
        
        with st.form("verification_form", clear_on_submit=False):
            code = st.text_input("Verification Code", placeholder="123456", max_chars=6)
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                verify_submitted = st.form_submit_button("Verify", type="primary", use_container_width=True)
            
            with col_btn2:
                resend_submitted = st.form_submit_button("Resend Code", use_container_width=True)
        
        if verify_submitted:
            if not code:
                st.error("Please enter the verification code")
            elif len(code) != 6:
                st.error("Verification code must be 6 digits")
            else:
                result = AuthService.verify_code(st.session_state.pending_user_id, code)
                
                if result['success']:
                    st.success("Account verified successfully! Please login.")
                    st.session_state.auth_page = 'login'
                    st.session_state.pending_user_id = None
                    st.session_state.verification_method = None
                    st.rerun()
                else:
                    st.error(result.get('error', 'Verification failed'))
        
        if resend_submitted:
            code_result = AuthService.create_verification_code(st.session_state.pending_user_id, st.session_state.verification_method)
            
            if code_result['success']:
                user = AuthService.get_user(st.session_state.pending_user_id)
                if st.session_state.verification_method == "email":
                    EmailService.send_verification_code(user['email'], code_result['code'])
                    st.success("Verification code resent to your email")
                else:
                    SMSService.send_verification_code(user['phone'], code_result['code'])
                    st.success("Verification code resent to your phone")
            else:
                st.error("Failed to resend code")

if not st.session_state.authenticated:
    show_auth_pages()
    st.stop()

st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stButton button {
        border-radius: 5px;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 16px;
        padding: 8px 16px;
    }
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns([1, 4, 2, 2])

with col1:
    st.markdown("### Impact Radar")

with col2:
    st.caption("Market-moving events, tracked to the second.")

with col3:
    user_display = st.session_state.user_email or st.session_state.user_phone or "User"
    admin_badge = " 👑 ADMIN" if user_is_admin() else ""
    st.caption(f"Logged in as: {user_display}{admin_badge}")

with col4:
    if st.button("Logout", type="secondary"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.user_phone = None
        st.session_state.is_admin = False
        st.rerun()

st.markdown("---")

page = st.tabs(["Dashboard", "Earnings", "Add Event", "Scanner Status", "Pricing", "Disclaimer"])

with page[0]:
    st.markdown("## Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["Watchlist", "Sectors", "Feed"])
    
    with tab1:
        st.markdown("### Watchlist")
        
        favorites = data_manager.get_events(favorites_only=True, upcoming_only=True)
        
        if favorites:
            for event in favorites:
                try:
                    event_date = datetime.strptime(event['date'], '%Y-%m-%d')
                    date_str = event_date.strftime('%b %d, %Y')
                except:
                    date_str = event['date']
                
                col1, col2, col3, col4, col5 = st.columns([1.5, 0.5, 2, 1.5, 4])
                
                with col1:
                    st.text(date_str)
                
                with col2:
                    if st.button('★', key=f"unfav_watch_{event['id']}"):
                        data_manager.toggle_favorite(int(event['id']))
                        st.rerun()
                
                with col3:
                    st.text(event['company'])
                
                with col4:
                    st.markdown(f"<span style='background-color: #000; color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;'>{event['ticker']}</span>", unsafe_allow_html=True)
                    st.caption(event.get('sector', 'Tech'))
                
                with col5:
                    st.text(event['title'])
                    source_url = event.get('source_url', '')
                    if source_url:
                        st.markdown(f"[Document]({source_url})", unsafe_allow_html=True)
                    else:
                        st.caption(f"Source: {event.get('source', 'Manual Entry')}")
                
                st.divider()
        else:
            st.info("No favorites yet. Click the star icon next to events in the Feed to add them to your watchlist.")
    
    with tab2:
        st.markdown("### Events by Sector")
        
        all_events = data_manager.get_events(upcoming_only=True)
        sector_counts = {}
        
        for event in all_events:
            sector = event.get('sector', 'Other')
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        if sector_counts:
            fig = go.Figure(data=[
                go.Bar(
                    x=list(sector_counts.keys()),
                    y=list(sector_counts.values()),
                    marker_color='black',
                    text=list(sector_counts.values()),
                    textposition='auto',
                )
            ])
            
            fig.update_layout(
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=400,
                margin=dict(l=40, r=40, t=40, b=40),
                xaxis=dict(
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0.5
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0.5
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        sectors = data_manager.get_all_sectors()
        
        for sector in sectors:
            sector_events = data_manager.get_events(sector=sector, upcoming_only=True)
            if sector_events:
                st.markdown(f"### {sector}")
                st.caption(f"{len(sector_events)} upcoming events")
                
                for event in sector_events[:3]:
                    st.markdown(f"**{event['company']}** ({event['ticker']}) - {event['title']}")
                    st.caption(f"Date: {event['date']}")
                
                st.markdown("")
        
        st.markdown("---")
        st.markdown("### Recent Scanner Findings")
        st.caption("Latest events discovered by automated scanners with proof links")
        
        scanner_events = data_manager.get_events(upcoming_only=False)
        scanner_events_with_urls = [e for e in scanner_events if e.get('source_url') and e.get('source_url').strip()]
        
        if scanner_events_with_urls:
            for event in sorted(scanner_events_with_urls, key=lambda x: x['date'], reverse=True)[:5]:
                col1, col2, col3 = st.columns([4, 1, 1])
                
                with col1:
                    st.markdown(f"**{event['company']}** ({event['ticker']}) - {event['title']}")
                    if event.get('summary'):
                        st.caption(event['summary'])
                    st.caption(f"Date: {event['date']} | Source: {event['source']}")
                
                with col2:
                    impact_score = event.get('impact_score', 50)
                    impact_color = '#FF6B6B' if impact_score < 60 else ('#FFD700' if impact_score < 80 else '#90EE90')
                    st.markdown(f"<div style='background-color: {impact_color}; padding: 8px 12px; border-radius: 8px; text-align: center;'><div style='font-size: 11px; color: #333;'>Impact</div><div style='font-size: 18px; font-weight: bold; color: #000;'>{impact_score}</div></div>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"[Document]({event['source_url']})", unsafe_allow_html=True)
                
                st.divider()
        else:
            st.info("No scanner events with proof links yet. Run a manual scan to populate.")
    
    with tab3:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            search = st.text_input("Search company, ticker...", placeholder="Search company, ticker...", label_visibility="collapsed", key="feed_search")
        
        with col2:
            sectors = ["All"] + data_manager.get_all_sectors()
            sector_filter = st.selectbox("Filter by sector", sectors, label_visibility="collapsed", key="feed_sector_filter")
        
        search_term = search.strip() if search else None
        sector_val = sector_filter if sector_filter != "All" else None
        
        events = data_manager.get_events(
            upcoming_only=True,
            sector=sector_val,
            search_term=search_term
        )
        
        if events:
            # Group events by company/ticker to show unique stocks
            companies_dict = {}
            for event in events:
                ticker = event['ticker']
                if ticker not in companies_dict:
                    companies_dict[ticker] = {
                        'company': event['company'],
                        'ticker': ticker,
                        'sector': event.get('sector', 'Tech'),
                        'events': [],
                        'is_tracked': False
                    }
                companies_dict[ticker]['events'].append(event)
                # Check if any event for this company is favorited
                if event.get('is_favorite'):
                    companies_dict[ticker]['is_tracked'] = True
            
            # Display unique companies
            for ticker, company_info in sorted(companies_dict.items()):
                # Get the nearest upcoming event date
                upcoming_dates = [e['date'] for e in company_info['events']]
                nearest_date = min(upcoming_dates)
                try:
                    event_date = datetime.strptime(nearest_date, '%Y-%m-%d')
                    date_str = event_date.strftime('%b %d, %Y')
                except:
                    date_str = nearest_date
                
                col1, col2, col3, col4, col5 = st.columns([1.5, 0.5, 2, 1.5, 4])
                
                with col1:
                    st.text(date_str)
                    if len(company_info['events']) > 1:
                        st.caption(f"+{len(company_info['events'])-1} more")
                
                with col2:
                    fav_icon = '★' if company_info['is_tracked'] else '☆'
                    # Use the first event's ID for the toggle
                    first_event_id = company_info['events'][0]['id']
                    if st.button(fav_icon, key=f"fav_company_{ticker}"):
                        data_manager.toggle_favorite(int(first_event_id))
                        st.rerun()
                
                with col3:
                    st.text(company_info['company'])
                
                with col4:
                    st.markdown(f"<span style='background-color: #000; color: #fff; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;'>{ticker}</span>", unsafe_allow_html=True)
                    st.caption(company_info['sector'])
                
                with col5:
                    st.text(f"{len(company_info['events'])} upcoming event{'s' if len(company_info['events']) > 1 else ''}")
                    # Show the first event as preview
                    st.caption(company_info['events'][0]['title'][:60] + "...")
                
                st.divider()
        else:
            st.info("No upcoming events. Run a manual scan in Scanner Status to populate events.")

with page[1]:
    st.markdown("## Earnings Tracker")
    st.caption("Track your portfolio and project earnings/losses based on upcoming events")
    
    ticker_input = st.text_input("Enter Stock Ticker", placeholder="e.g., AAPL", key="earnings_ticker").upper()
    
    if ticker_input:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker_input)
            info = stock.info
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.markdown(f"### {info.get('longName', ticker_input)}")
                    st.markdown(f"**Ticker:** {ticker_input}")
                    st.markdown(f"**Current Price:** ${current_price:.2f}")
                    
                    investment_amount = st.number_input(
                        "Your Investment Amount ($)",
                        min_value=0.0,
                        value=1000.0,
                        step=100.0,
                        key="investment_amount"
                    )
                    
                    shares_owned = investment_amount / current_price
                    st.caption(f"Shares owned: {shares_owned:.2f}")
                
                with col2:
                    st.markdown("### Portfolio Projection")
                    
                    upcoming_events = data_manager.get_events(ticker=ticker_input, upcoming_only=True)
                    
                    if upcoming_events:
                        st.markdown("Based on upcoming events:")
                        
                        total_impact = 0
                        for event in upcoming_events:
                            impact = event.get('impact_score', 50)
                            total_impact += impact
                        
                        avg_impact = total_impact / len(upcoming_events)
                        
                        projected_change_pct = (avg_impact - 50) / 10
                        
                        projected_price = current_price * (1 + projected_change_pct / 100)
                        projected_pl = (projected_price - current_price) * shares_owned
                        projected_pl_pct = ((projected_price - current_price) / current_price) * 100
                        
                        if projected_pl > 0:
                            st.success(f"Potential Gain: ${projected_pl:.2f} (+{projected_pl_pct:.2f}%)")
                        else:
                            st.error(f"Potential Loss: ${projected_pl:.2f} ({projected_pl_pct:.2f}%)")
                        
                        st.caption(f"Projected Price: ${projected_price:.2f}")
                        st.caption(f"Current Price: ${current_price:.2f}")
                        st.caption(f"Based on {len(upcoming_events)} upcoming events (Avg Impact: {avg_impact:.0f})")
                    else:
                        st.info("No upcoming events found for this ticker")
                
                st.markdown("---")
                st.markdown("### Upcoming Events")
                
                if upcoming_events:
                    for event in upcoming_events:
                        col1, col2, col3 = st.columns([3, 1, 2])
                        
                        with col1:
                            st.markdown(f"**{event['title']}**")
                            st.caption(f"{event['event_type']} - {event['date']}")
                        
                        with col2:
                            impact_score = event.get('impact_score', 50)
                            impact_color = '#FF6B6B' if impact_score < 60 else ('#FFD700' if impact_score < 80 else '#90EE90')
                            st.markdown(f"<div style='background-color: {impact_color}; padding: 8px 12px; border-radius: 8px; text-align: center;'><div style='font-size: 11px; color: #333;'>Impact</div><div style='font-size: 18px; font-weight: bold; color: #000;'>{impact_score}</div></div>", unsafe_allow_html=True)
                        
                        with col3:
                            price_impact_pct = (impact_score - 50) / 10
                            price_impact_dollars = (current_price * price_impact_pct / 100) * shares_owned
                            
                            if price_impact_dollars > 0:
                                st.markdown(f"**Potential: +${price_impact_dollars:.2f}**")
                            else:
                                st.markdown(f"**Potential: ${price_impact_dollars:.2f}**")
                            st.caption(f"Per share: ${current_price * price_impact_pct / 100:.2f}")
                        
                        st.divider()
                else:
                    st.info(f"No upcoming events tracked for {ticker_input}. Add events in the 'Add Event' tab.")
            else:
                st.error(f"Could not fetch data for ticker {ticker_input}. Please check if the ticker is valid.")
        
        except Exception as e:
            st.error(f"Error fetching stock data: {str(e)}")
    else:
        st.info("Enter a stock ticker above to view earnings projections and track your portfolio")

with page[2]:
    st.markdown("## Add New Event")
    st.caption("Manually track upcoming releases and innovations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.text_input("Stock Ticker", placeholder="e.g., AAPL").upper()
        company_name = st.text_input("Company Name", placeholder="e.g., Apple Inc.")
        event_type = st.selectbox(
            "Event Type",
            ["Product Launch", "FDA Approval", "Earnings Report", "SEC Filing", "Partnership Announcement", "Other"]
        )
        title = st.text_input("Event Title", placeholder="e.g., iPhone 18 Launch")
    
    with col2:
        description = st.text_area("Description", placeholder="Describe the event and its potential impact...")
        event_date = st.date_input("Event Date")
        impact_score = st.slider("Impact Score (0-100)", 0, 100, 50, 
                                help="Estimated impact on stock price")
        sector = st.selectbox("Sector", ["Tech", "Pharma", "Gaming", "Retail", "Finance", "Healthcare", "Other"])
    
    if st.button("Add Event", type="primary"):
        if ticker and company_name and title:
            event_data = {
                "ticker": ticker,
                "company": company_name,
                "event_type": event_type,
                "title": title,
                "description": description,
                "date": event_date.strftime('%Y-%m-%d'),
                "impact_score": impact_score,
                "source": "Manual Entry",
                "subsidiary": None,
                "sector": sector
            }
            
            data_manager.add_event(event_data)
            st.success(f"Event '{title}' added successfully for {ticker}")
            st.rerun()
        else:
            st.error("Please fill in ticker, company name, and event title.")

with page[3]:
    st.markdown("## Automated Scanner Status")
    st.caption("Monitor the automated scanning bots for SEC, FDA, and company releases")
    
    status = scanner_service.get_scanner_status()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### SEC EDGAR Scanner")
        if status['is_running']:
            st.success("Active")
        else:
            st.warning("Idle")
        st.caption("Runs every 4 hours")
        st.caption("Monitoring: 8-K, 10-Q, 10-K filings")
        st.caption(f"Tracked companies: {len(data_manager.get_companies(tracked_only=True))}")
    
    with col2:
        st.markdown("### FDA Scanner")
        if status['is_running']:
            st.success("Active")
        else:
            st.warning("Idle")
        st.caption("Runs every 6 hours")
        st.caption("Monitoring: Drug approvals, clinical trials")
        st.caption(f"Total scans: {status['total_scans']}")
    
    with col3:
        st.markdown("### Company Releases Scanner")
        if status['is_running']:
            st.success("Active")
        else:
            st.warning("Idle")
        st.caption("Runs every 8 hours")
        st.caption("Monitoring: Product launches, events")
        if status.get('last_scan'):
            try:
                last_scan_time = datetime.fromisoformat(status['last_scan'])
                st.caption(f"Last: {last_scan_time.strftime('%Y-%m-%d %H:%M')}")
            except:
                st.caption(f"Last: {status['last_scan']}")
    
    st.markdown("---")
    st.markdown("### Recent Scanner Activity")
    
    activity_logs = scanner_service.get_recent_logs(limit=20)
    
    if activity_logs:
        for log in activity_logs:
            try:
                timestamp = datetime.fromisoformat(log['timestamp'])
                time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                level_badge = {
                    "success": "✓",
                    "warning": "!",
                    "error": "×",
                    "info": "i"
                }.get(log['level'], "i")
                
                st.markdown(f"**{time_str}** - {log['scanner']}: {level_badge} {log['message']}")
            except Exception as e:
                st.caption(f"{log['scanner']}: {log['message']}")
    else:
        st.info("No scanner activity yet. Run a manual scan to populate logs.")
    
    st.markdown("---")
    st.markdown("### Scanner Discoveries with Impact Scores")
    st.caption("Events automatically discovered by scanners with impact analysis")
    
    scanner_events = data_manager.get_events(upcoming_only=False)
    scanner_events_with_impact = [e for e in scanner_events if e.get('source_url') and e.get('source_url').strip() and e.get('impact_score')]
    
    if scanner_events_with_impact:
        for event in sorted(scanner_events_with_impact, key=lambda x: x['date'], reverse=True)[:10]:
            col1, col2, col3 = st.columns([4, 1, 1])
            
            with col1:
                st.markdown(f"**{event['company']}** ({event['ticker']}) - {event['title']}")
                st.caption(f"Date: {event['date']} | Source: {event['source']}")
            
            with col2:
                impact_score = event.get('impact_score', 50)
                impact_color = '#FF6B6B' if impact_score < 60 else ('#FFD700' if impact_score < 80 else '#90EE90')
                st.markdown(f"<div style='background-color: {impact_color}; padding: 6px 10px; border-radius: 6px; text-align: center;'><div style='font-size: 10px; color: #333;'>Impact</div><div style='font-size: 16px; font-weight: bold; color: #000;'>{impact_score}</div></div>", unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"[Document]({event['source_url']})", unsafe_allow_html=True)
            
            # Display detailed summary
            if event.get('summary'):
                with st.expander("View Detailed Analysis"):
                    st.markdown(f"**Stock Price Impact Analysis:**")
                    st.write(event['summary'])
            
            st.divider()
    else:
        st.info("No scanner discoveries yet. Run a manual scan to populate findings.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Run Manual Scan Now", type="primary", use_container_width=True):
            with st.spinner("Scanning SEC EDGAR, FDA, and company releases..."):
                scanner_service.run_manual_scan()
            st.success("Manual scan completed")
            st.rerun()
    
    with col2:
        if status['is_running']:
            if st.button("Pause Scanner", use_container_width=True):
                scanner_service.stop()
                st.info("Scanner service paused")
                st.rerun()
        else:
            if st.button("Start Scanner", use_container_width=True):
                scanner_service.start()
                st.success("Scanner service started")
                st.rerun()

with page[4]:
    st.markdown("## Simple, transparent pricing")
    st.markdown("")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Free")
        st.markdown("# $0")
        st.markdown("---")
        st.markdown("✓ 1 watchlist")
        st.markdown("✓ Weekly digest")
        st.markdown("✓ Basic feed")
        st.markdown("")
        st.markdown("")
        if st.button("Get started", use_container_width=True, key="free_plan"):
            st.info("Free tier is active by default. No signup required.")
    
    with col2:
        st.markdown("### Pro")
        st.markdown("# $29/mo")
        st.markdown("---")
        st.markdown("✓ Unlimited watchlists")
        st.markdown("✓ Real-time alerts")
        st.markdown("✓ Impact scoring")
        st.markdown("✓ Sector filters")
        st.markdown("")
        if st.button("Start Pro", type="primary", use_container_width=True, key="pro_plan"):
            st.session_state.selected_plan = "pro"
            st.session_state.show_payment_options = True
    
    with col3:
        st.markdown("### Team")
        st.markdown("# $99/mo")
        st.markdown("---")
        st.markdown("✓ Everything in Pro")
        st.markdown("✓ Slack/Discord integration")
        st.markdown("✓ Historical export")
        st.markdown("✓ API access")
        st.markdown("")
        if st.button("Contact sales", use_container_width=True, key="team_plan"):
            st.session_state.selected_plan = "team"
            st.session_state.show_payment_options = True
    
    if st.session_state.get('show_payment_options'):
        st.markdown("---")
        st.markdown(f"### Complete your {st.session_state.selected_plan.title()} plan purchase")
        
        payment_method = st.radio(
            "Choose payment method:",
            ["Credit/Debit Card (Stripe)", "Cryptocurrency"],
            horizontal=True
        )
        
        if payment_method == "Credit/Debit Card (Stripe)":
            if payment_service.is_stripe_configured():
                if st.button("Proceed to Stripe Checkout", type="primary"):
                    checkout_url = payment_service.create_checkout_session(
                        plan=st.session_state.selected_plan,
                        success_url="https://releaseradar.com/success",
                        cancel_url="https://releaseradar.com/pricing"
                    )
                    if checkout_url:
                        st.success(f"Redirecting to Stripe checkout...")
                        st.markdown(f"[Click here if not redirected]({checkout_url})")
                    else:
                        st.error("Unable to create checkout session. Please try again.")
            else:
                st.warning("Stripe integration pending. Please configure STRIPE_SECRET_KEY to enable card payments.")
                st.info("For now, you can use cryptocurrency payment below.")
        
        else:
            crypto_payment = payment_service.create_crypto_payment(
                plan=st.session_state.selected_plan,
                wallet_address=""
            )
            
            st.markdown(f"**Plan:** {crypto_payment['plan']}")
            st.markdown(f"**Price:** ${crypto_payment['usd_price']}/month")
            st.markdown("")
            st.markdown("**Send payment to one of these addresses:**")
            
            for crypto, address in crypto_payment['crypto_wallets'].items():
                st.code(f"{crypto}: {address}", language="")
            
            st.info(crypto_payment['instructions'])
            st.caption(crypto_payment['note'])
            
            email = st.text_input("Your email address (for confirmation):", key="crypto_email")
            
            if st.button("I've sent the payment", type="primary"):
                if email:
                    st.success(f"Thank you! We'll verify your payment and send confirmation to {email} within 24 hours.")
                    st.session_state.show_payment_options = False
                else:
                    st.error("Please provide your email address.")
    
    st.markdown("---")
    st.markdown("")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Payment Methods")
        st.markdown("We accept:")
        st.markdown("- Credit/Debit Cards (via Stripe)")
        st.markdown("- Cryptocurrency (BTC, ETH, USDC, USDT)")
        st.markdown("- ACH transfers (Team plan)")
    
    with col2:
        st.markdown("### FAQ")
        with st.expander("Can I cancel anytime?"):
            st.write("Yes, cancel anytime. No questions asked.")
        with st.expander("Do you offer refunds?"):
            st.write("Yes, 30-day money-back guarantee for all paid plans.")
        with st.expander("What cryptocurrencies do you accept?"):
            st.write("BTC, ETH, USDC, and USDT.")

with page[5]:
    st.markdown("## Disclaimer")
    
    st.markdown("""
    ### Important Legal Disclaimer
    
    #### Not Financial Advice
    
    The information provided on Impact Radar is for **informational and educational purposes only** 
    and should not be construed as financial advice, investment recommendations, or any form of 
    professional guidance.
    
    #### No Warranties
    
    Impact Radar makes no representations or warranties regarding the accuracy, completeness, or 
    timeliness of any information displayed on this platform. All data is gathered from publicly 
    available sources and may contain errors, omissions, or be outdated.
    
    #### Investment Risks
    
    - Stock investments carry inherent risks, including the potential loss of principal
    - Past performance does not guarantee future results
    - Company releases and innovations may not affect stock prices as anticipated
    - Market conditions can change rapidly and unpredictably
    
    #### User Responsibility
    
    Users of Impact Radar are solely responsible for their own investment decisions. Before making 
    any investment, you should:
    
    1. Conduct your own thorough research
    2. Consult with qualified financial advisors
    3. Consider your individual financial situation and risk tolerance
    4. Verify all information from primary sources
    
    #### Data Sources
    
    Information on Impact Radar is aggregated from various public sources, including but not limited to:
    
    - **SEC EDGAR** - U.S. Securities and Exchange Commission filings
    - **FDA** - U.S. Food and Drug Administration announcements
    - **Yahoo Finance** - Stock price data via yfinance library
    - **Company Press Releases** - Official company announcements
    - **User Submissions** - Manually entered events and data
    
    #### Limitation of Liability
    
    Impact Radar, its developers, and operators shall not be held liable for any losses, damages, 
    or adverse outcomes resulting from the use of information provided on this platform.
    
    #### No Affiliation
    
    Impact Radar is not affiliated with, endorsed by, or sponsored by any of the companies, 
    regulatory agencies, or data sources mentioned on this platform.
    
    #### Updates and Changes
    
    This disclaimer may be updated periodically. Continued use of Impact Radar constitutes 
    acceptance of any changes to this disclaimer.
    
    ---
    
    **Last Updated:** November 8, 2025
    
    By using Impact Radar, you acknowledge that you have read, understood, and agree to this disclaimer.
    """)
    
    st.markdown("---")
    st.caption("Impact Radar v2.0 | For informational purposes only")

st.markdown("---")
st.caption("© 2025 Impact Radar | Data from public sources")
