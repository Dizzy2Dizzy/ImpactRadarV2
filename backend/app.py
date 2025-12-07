"""
Impact Radar - Event-Driven Signal Engine

Professional platform for active equity and biotech traders and small funds.
Ingests SEC, FDA, and corporate events with deterministic impact scoring.
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from data_manager import DataManager
from scanner_service import get_scanner_service
from auth_service import AuthService
from email_service import EmailService
from sms_service import SMSService
import yfinance as yf

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Impact Radar - Event Signal Engine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# AUTHENTICATION
# ============================================================================

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'auth_page' not in st.session_state:
    st.session_state.auth_page = 'login'
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'Events'
if 'sidebar_open' not in st.session_state:
    st.session_state.sidebar_open = False

def user_is_admin():
    """Check if current user has admin privileges."""
    return st.session_state.get('is_admin', False)

# Authentication pages (keeping existing auth system)
from auth_service import AuthService

def show_auth_pages():
    """Display authentication pages."""
    st.markdown("### Impact Radar")
    st.caption("Event-driven signal engine for active traders and funds")
    st.markdown("---")
    
    if st.session_state.auth_page == 'login':
        show_login_page()
    elif st.session_state.auth_page == 'signup':
        show_signup_page()
    elif st.session_state.auth_page == 'verify':
        show_verification_page()

def show_login_page():
    """Login page."""
    st.markdown("## Access Your Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
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
    """Signup page."""
    st.markdown("## Create Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("signup_form"):
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
    """Verification page."""
    st.markdown("## Verify Your Account")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info(f"A verification code has been sent to your {st.session_state.verification_method}.")
        
        with st.form("verification_form"):
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

# ============================================================================
# MAIN APPLICATION (POST-AUTH)
# ============================================================================

# TradingView-inspired professional styling
st.markdown("""
<style>
    /* ========================================
       TRADINGVIEW-STYLE COLOR PALETTE
       ======================================== */
    :root {
        --tv-bg-dark: #131722;
        --tv-bg-panel: #1e222d;
        --tv-bg-card: #2a2e39;
        --tv-bg-hover: #363a45;
        --tv-border: #363a45;
        --tv-text-primary: #d1d4dc;
        --tv-text-secondary: #787b86;
        --tv-text-muted: #5d606b;
        --tv-accent-green: #26a69a;
        --tv-accent-red: #ef5350;
        --tv-accent-blue: #2196f3;
        --tv-accent-yellow: #ffeb3b;
        --tv-accent-orange: #ff9800;
    }
    
    /* ========================================
       BASE STYLING
       ======================================== */
    .main > div {
        padding-top: 1rem;
        background-color: var(--tv-bg-dark) !important;
    }
    
    [data-testid="stSidebar"] {display: none;}
    
    .stApp {
        background-color: #131722 !important;
    }
    
    /* ========================================
       PREMIUM SIDEBAR NAVIGATION
       ======================================== */
    .sidebar-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0, 0, 0, 0.5);
        z-index: 998;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    
    .sidebar-overlay.open {
        opacity: 1;
        visibility: visible;
    }
    
    .sidebar-nav {
        position: fixed;
        top: 0;
        left: -280px;
        width: 280px;
        height: 100vh;
        background: linear-gradient(180deg, #1e222d 0%, #131722 100%);
        border-right: 1px solid #363a45;
        z-index: 999;
        transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        display: flex;
        flex-direction: column;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
    }
    
    .sidebar-nav.open {
        left: 0;
    }
    
    .sidebar-header {
        padding: 24px 20px;
        border-bottom: 1px solid #363a45;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .sidebar-logo {
        font-size: 18px;
        font-weight: 700;
        color: #d1d4dc;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .sidebar-logo-icon {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }
    
    .sidebar-close {
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background-color: transparent;
        border: none;
        color: #787b86;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
        font-size: 20px;
    }
    
    .sidebar-close:hover {
        background-color: #2a2e39;
        color: #d1d4dc;
    }
    
    .sidebar-menu {
        flex: 1;
        padding: 16px 12px;
        overflow-y: auto;
    }
    
    .sidebar-section {
        margin-bottom: 24px;
    }
    
    .sidebar-section-title {
        font-size: 11px;
        font-weight: 600;
        color: #5d606b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0 8px;
        margin-bottom: 8px;
    }
    
    .sidebar-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        border-radius: 8px;
        color: #787b86;
        cursor: pointer;
        transition: all 0.2s ease;
        margin-bottom: 4px;
        text-decoration: none;
        font-size: 14px;
        font-weight: 500;
    }
    
    .sidebar-item:hover {
        background-color: #2a2e39;
        color: #d1d4dc;
        transform: translateX(4px);
    }
    
    .sidebar-item.active {
        background: linear-gradient(90deg, rgba(33, 150, 243, 0.15) 0%, rgba(33, 150, 243, 0.05) 100%);
        color: #2196f3;
        border-left: 3px solid #2196f3;
        padding-left: 13px;
    }
    
    .sidebar-item-icon {
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }
    
    .sidebar-footer {
        padding: 16px 20px;
        border-top: 1px solid #363a45;
    }
    
    .sidebar-user {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        background-color: #2a2e39;
        border-radius: 8px;
    }
    
    .sidebar-user-avatar {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #26a69a 0%, #00897b 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 600;
        font-size: 14px;
    }
    
    .sidebar-user-info {
        flex: 1;
        overflow: hidden;
    }
    
    .sidebar-user-name {
        font-size: 13px;
        font-weight: 600;
        color: #d1d4dc;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .sidebar-user-role {
        font-size: 11px;
        color: #787b86;
    }
    
    /* Menu Toggle Button */
    .menu-toggle {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        background-color: #1e222d;
        border: 1px solid #363a45;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.2s ease;
        color: #d1d4dc;
        font-size: 20px;
    }
    
    .menu-toggle:hover {
        background-color: #2a2e39;
        border-color: #2196f3;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
    }
    
    /* Page Title */
    .page-title {
        font-size: 24px;
        font-weight: 700;
        color: #d1d4dc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .page-title-icon {
        font-size: 24px;
    }
    
    /* ========================================
       SKELETON LOADING ANIMATION
       ======================================== */
    @keyframes skeleton-pulse {
        0% { background-position: -200px 0; }
        100% { background-position: calc(200px + 100%) 0; }
    }
    
    .skeleton {
        background: linear-gradient(90deg, #2a2e39 0%, #363a45 50%, #2a2e39 100%);
        background-size: 200px 100%;
        animation: skeleton-pulse 1.5s ease-in-out infinite;
        border-radius: 4px;
    }
    
    .skeleton-text {
        height: 16px;
        margin-bottom: 8px;
    }
    
    .skeleton-title {
        height: 24px;
        width: 60%;
        margin-bottom: 12px;
    }
    
    .skeleton-card {
        height: 120px;
        border-radius: 8px;
        margin-bottom: 16px;
    }
    
    .skeleton-metric {
        height: 48px;
        width: 80px;
        border-radius: 8px;
    }
    
    /* ========================================
       TABS - TRADINGVIEW STYLE
       ======================================== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e222d;
        padding: 8px 12px;
        border-radius: 8px;
        border-bottom: 1px solid #363a45;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
        font-weight: 500;
        color: #787b86;
        background-color: transparent;
        border-radius: 6px;
        padding: 8px 16px;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: #d1d4dc;
        background-color: #2a2e39;
    }
    
    .stTabs [aria-selected="true"] {
        color: #d1d4dc !important;
        background-color: #2a2e39 !important;
        border-bottom: 2px solid #2196f3 !important;
    }
    
    /* ========================================
       BUTTONS - SMOOTH TRANSITIONS
       ======================================== */
    .stButton > button {
        background-color: #2a2e39 !important;
        color: #d1d4dc !important;
        border: 1px solid #363a45 !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #363a45 !important;
        border-color: #2196f3 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
    }
    
    .stButton > button[kind="primary"] {
        background-color: #2196f3 !important;
        border-color: #2196f3 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1976d2 !important;
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
    }
    
    /* ========================================
       INPUTS - TRADINGVIEW STYLE
       ======================================== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #2a2e39 !important;
        border: 1px solid #363a45 !important;
        border-radius: 6px !important;
        color: #d1d4dc !important;
        transition: all 0.2s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {
        border-color: #2196f3 !important;
        box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2) !important;
    }
    
    /* ========================================
       CARDS & CONTAINERS
       ======================================== */
    .stExpander {
        background-color: #1e222d !important;
        border: 1px solid #363a45 !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    
    .stExpander:hover {
        border-color: #2196f3 !important;
    }
    
    .stExpander > div > div > div > div {
        color: #d1d4dc !important;
    }
    
    /* ========================================
       METRICS & DATA DISPLAY
       ======================================== */
    [data-testid="stMetricValue"] {
        color: #d1d4dc !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricDelta"] svg {
        stroke: currentColor !important;
    }
    
    /* ========================================
       IMPACT INDICATORS
       ======================================== */
    .impact-high {
        color: #26a69a !important;
        font-weight: 600;
    }
    
    .impact-medium {
        color: #ff9800 !important;
        font-weight: 600;
    }
    
    .impact-low {
        color: #ef5350 !important;
        font-weight: 600;
    }
    
    /* ========================================
       EVENT CARDS - SMOOTH HOVER
       ======================================== */
    .event-card {
        background-color: #1e222d;
        border: 1px solid #363a45;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        transition: all 0.2s ease;
    }
    
    .event-card:hover {
        border-color: #2196f3;
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }
    
    /* ========================================
       IMPACT SCORE BADGE
       ======================================== */
    .impact-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 48px;
        height: 48px;
        border-radius: 8px;
        font-size: 18px;
        font-weight: 700;
        transition: all 0.2s ease;
    }
    
    .impact-badge:hover {
        transform: scale(1.05);
    }
    
    .impact-badge.high {
        background: linear-gradient(135deg, #26a69a 0%, #00897b 100%);
        color: #fff;
    }
    
    .impact-badge.medium {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        color: #fff;
    }
    
    .impact-badge.low {
        background: linear-gradient(135deg, #ef5350 0%, #d32f2f 100%);
        color: #fff;
    }
    
    /* ========================================
       DIRECTION INDICATORS
       ======================================== */
    .direction-positive {
        color: #26a69a;
    }
    
    .direction-positive::before {
        content: "▲ ";
    }
    
    .direction-negative {
        color: #ef5350;
    }
    
    .direction-negative::before {
        content: "▼ ";
    }
    
    .direction-neutral {
        color: #787b86;
    }
    
    .direction-neutral::before {
        content: "● ";
    }
    
    /* ========================================
       TABLES
       ======================================== */
    .stDataFrame {
        border: 1px solid #363a45 !important;
        border-radius: 8px !important;
        overflow: hidden;
    }
    
    .stDataFrame thead tr th {
        background-color: #2a2e39 !important;
        color: #d1d4dc !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #363a45 !important;
    }
    
    .stDataFrame tbody tr {
        transition: background-color 0.15s ease;
    }
    
    .stDataFrame tbody tr:hover {
        background-color: #2a2e39 !important;
    }
    
    /* ========================================
       ALERTS & MESSAGES
       ======================================== */
    .stAlert {
        border-radius: 8px !important;
        border: none !important;
    }
    
    [data-testid="stNotificationContentSuccess"] {
        background-color: rgba(38, 166, 154, 0.1) !important;
        border-left: 4px solid #26a69a !important;
    }
    
    [data-testid="stNotificationContentError"] {
        background-color: rgba(239, 83, 80, 0.1) !important;
        border-left: 4px solid #ef5350 !important;
    }
    
    [data-testid="stNotificationContentWarning"] {
        background-color: rgba(255, 152, 0, 0.1) !important;
        border-left: 4px solid #ff9800 !important;
    }
    
    [data-testid="stNotificationContentInfo"] {
        background-color: rgba(33, 150, 243, 0.1) !important;
        border-left: 4px solid #2196f3 !important;
    }
    
    /* ========================================
       DIVIDERS
       ======================================== */
    hr {
        border-color: #363a45 !important;
        opacity: 0.5;
    }
    
    /* ========================================
       SCROLLBARS - TRADINGVIEW STYLE
       ======================================== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1e222d;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #363a45;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #4a4e59;
    }
    
    /* ========================================
       REAL-TIME UPDATE PULSE
       ======================================== */
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(38, 166, 154, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(38, 166, 154, 0); }
        100% { box-shadow: 0 0 0 0 rgba(38, 166, 154, 0); }
    }
    
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 83, 80, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(239, 83, 80, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 83, 80, 0); }
    }
    
    .pulse-positive {
        animation: pulse-green 2s infinite;
    }
    
    .pulse-negative {
        animation: pulse-red 2s infinite;
    }
    
    /* ========================================
       LOADING SPINNER OVERRIDE
       ======================================== */
    .stSpinner > div {
        border-top-color: #2196f3 !important;
    }
    
    /* ========================================
       SLIDER STYLING
       ======================================== */
    .stSlider > div > div > div {
        background-color: #363a45 !important;
    }
    
    .stSlider > div > div > div > div {
        background-color: #2196f3 !important;
    }
    
    /* ========================================
       CHECKBOX & RADIO
       ======================================== */
    .stCheckbox > label,
    .stRadio > label {
        transition: color 0.15s ease;
    }
    
    .stCheckbox > label:hover,
    .stRadio > label:hover {
        color: #d1d4dc !important;
    }
    
    /* ========================================
       CAPTION TEXT
       ======================================== */
    .stCaption, small {
        color: #787b86 !important;
    }
    
    /* ========================================
       MARKDOWN HEADERS
       ======================================== */
    h1, h2, h3 {
        color: #d1d4dc !important;
    }
    
    /* ========================================
       LINKS
       ======================================== */
    a {
        color: #2196f3 !important;
        transition: color 0.15s ease;
    }
    
    a:hover {
        color: #64b5f6 !important;
    }
</style>
""", unsafe_allow_html=True)

# Skeleton loading component helper
def show_skeleton(type="card", count=1):
    """Display skeleton loading placeholders."""
    skeleton_html = ""
    for _ in range(count):
        if type == "card":
            skeleton_html += '<div class="skeleton skeleton-card"></div>'
        elif type == "text":
            skeleton_html += '<div class="skeleton skeleton-text"></div>'
        elif type == "title":
            skeleton_html += '<div class="skeleton skeleton-title"></div>'
        elif type == "metric":
            skeleton_html += '<div class="skeleton skeleton-metric"></div>'
    st.markdown(skeleton_html, unsafe_allow_html=True)

# Navigation menu items with icons
MENU_ITEMS = [
    {"id": "Events", "icon": "📊", "label": "Events", "section": "Market Data"},
    {"id": "Companies", "icon": "🏢", "label": "Companies", "section": "Market Data"},
    {"id": "Modeling", "icon": "🔬", "label": "Modeling", "section": "Analytics"},
    {"id": "Watchlist", "icon": "⭐", "label": "Watchlist", "section": "Personal"},
    {"id": "Earnings", "icon": "💰", "label": "Earnings", "section": "Personal"},
    {"id": "Scanner Status", "icon": "🔍", "label": "Scanner Status", "section": "System"},
    {"id": "Account", "icon": "👤", "label": "Account", "section": "System"},
]

def toggle_sidebar():
    """Toggle sidebar open/close state."""
    st.session_state.sidebar_open = not st.session_state.sidebar_open

def navigate_to(page):
    """Navigate to a specific page and close sidebar."""
    st.session_state.current_page = page
    st.session_state.sidebar_open = False

# Get user display info
user_display = st.session_state.user_email or st.session_state.user_phone or "User"
user_initial = user_display[0].upper() if user_display else "U"
admin_badge = "Admin" if user_is_admin() else "Member"

# Render sidebar HTML
sidebar_open_class = "open" if st.session_state.sidebar_open else ""

# Group menu items by section
sections = {}
for item in MENU_ITEMS:
    section = item["section"]
    if section not in sections:
        sections[section] = []
    sections[section].append(item)

# Build menu HTML
menu_html = ""
for section_name, items in sections.items():
    menu_html += f'<div class="sidebar-section"><div class="sidebar-section-title">{section_name}</div>'
    for item in items:
        active_class = "active" if st.session_state.current_page == item["id"] else ""
        menu_html += f'''
            <div class="sidebar-item {active_class}" id="nav-{item['id'].replace(' ', '-').lower()}">
                <span class="sidebar-item-icon">{item['icon']}</span>
                <span>{item['label']}</span>
            </div>
        '''
    menu_html += '</div>'

st.markdown(f"""
    <div class="sidebar-overlay {sidebar_open_class}" id="sidebar-overlay"></div>
    <nav class="sidebar-nav {sidebar_open_class}" id="sidebar-nav">
        <div class="sidebar-header">
            <div class="sidebar-logo">
                <div class="sidebar-logo-icon">📡</div>
                <span>Impact Radar</span>
            </div>
        </div>
        <div class="sidebar-menu">
            {menu_html}
        </div>
        <div class="sidebar-footer">
            <div class="sidebar-user">
                <div class="sidebar-user-avatar">{user_initial}</div>
                <div class="sidebar-user-info">
                    <div class="sidebar-user-name">{user_display[:25]}</div>
                    <div class="sidebar-user-role">{admin_badge}</div>
                </div>
            </div>
        </div>
    </nav>
""", unsafe_allow_html=True)

# Header with menu toggle
col_menu, col_title, col_spacer, col_logout = st.columns([0.5, 6, 3, 1])

with col_menu:
    if st.button("☰", key="menu_toggle", help="Open navigation menu"):
        toggle_sidebar()
        st.rerun()

with col_title:
    # Get current page icon
    current_icon = "📊"
    for item in MENU_ITEMS:
        if item["id"] == st.session_state.current_page:
            current_icon = item["icon"]
            break
    st.markdown(f"<h1 class='page-title'><span class='page-title-icon'>{current_icon}</span> {st.session_state.current_page}</h1>", unsafe_allow_html=True)

with col_logout:
    if st.button("Logout", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.user_email = None
        st.session_state.is_admin = False
        st.rerun()

st.markdown("---")

# Navigation buttons (hidden, triggered by JavaScript would be ideal, but we use Streamlit buttons)
# Create a row of navigation buttons that are styled to look hidden but functional
nav_cols = st.columns(len(MENU_ITEMS))
for i, item in enumerate(MENU_ITEMS):
    with nav_cols[i]:
        if st.session_state.sidebar_open:
            if st.button(f"{item['icon']} {item['label']}", key=f"nav_btn_{item['id']}", use_container_width=True):
                navigate_to(item['id'])
                st.rerun()

# Hide the navigation buttons row when sidebar is closed
if not st.session_state.sidebar_open:
    st.markdown("""
        <style>
            div[data-testid="column"]:has(button[kind="secondary"]:not([data-testid="baseButton-secondary"])) {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

# Initialize services
dm = DataManager()
scanner_service = get_scanner_service()

# ============================================================================
# EVENTS PAGE
# ============================================================================

if st.session_state.current_page == "Events":
    st.markdown("## Event Feed")
    st.caption("Real-time SEC, FDA, and corporate events with impact analysis")
    
    # Filters in expander
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            date_filter = st.select_slider(
                "Time Horizon",
                options=["Past 7 days", "Past 30 days", "Past 90 days", "Next 7 days", "Next 30 days", "All"],
                value="All",
                key="events_date_filter"
            )
        
        with col2:
            sector_filter = st.selectbox(
                "Sector",
                ["All Sectors", "Tech", "Pharma", "Finance", "Gaming", "Retail", "Other"],
                key="events_sector_filter"
            )
        
        with col3:
            direction_filter = st.selectbox(
                "Direction",
                ["All", "Positive", "Negative", "Neutral", "Uncertain"],
                key="events_direction_filter"
            )
        
        with col4:
            min_impact = st.slider("Min Impact Score", 0, 100, 0, key="events_min_impact")
        
        col5, col6 = st.columns(2)
        
        with col5:
            event_type_filter = st.multiselect(
                "Event Types",
                ["earnings", "fda_approval", "fda_rejection", "sec_8k", "sec_10k", "sec_10q", "product_launch", "guidance_raise", "guidance_lower"],
                default=[],
                key="events_type_filter"
            )
        
        with col6:
            watchlist_only = st.checkbox("Watchlist Only", value=False, key="events_watchlist_only")
    
    # Apply filters
    start_date = None
    end_date = None
    upcoming_only = False
    
    if "Next" in date_filter:
        upcoming_only = True
        if "7" in date_filter:
            end_date = datetime.utcnow() + timedelta(days=7)
        elif "30" in date_filter:
            end_date = datetime.utcnow() + timedelta(days=30)
    elif "Past" in date_filter:
        if "7" in date_filter:
            start_date = datetime.utcnow() - timedelta(days=7)
        elif "30" in date_filter:
            start_date = datetime.utcnow() - timedelta(days=30)
        elif "90" in date_filter:
            start_date = datetime.utcnow() - timedelta(days=90)
    
    # Get filtered events
    events = dm.get_events(
        sector=None if sector_filter == "All Sectors" else sector_filter,
        direction=None if direction_filter == "All" else direction_filter.lower(),
        min_impact=min_impact,
        start_date=start_date,
        end_date=end_date,
        upcoming_only=upcoming_only,
        watchlist_only=watchlist_only,
        user_id=st.session_state.user_id if watchlist_only else None,
        limit=100
    )
    
    # Filter by event type if selected
    if event_type_filter:
        events = [e for e in events if e['event_type'] in event_type_filter]
    
    st.markdown(f"<span style='color: #787b86;'>{len(events)} events</span>", unsafe_allow_html=True)
    
    # Display events with TradingView-style cards
    if events:
        for event in events:
            # Format date
            event_date = event['date']
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date)
                except:
                    pass
            
            date_str = event_date.strftime('%b %d, %Y %H:%M') if isinstance(event_date, datetime) else str(event_date)
            
            # Direction styling
            direction = event.get('direction', 'neutral')
            if direction == 'positive':
                dir_class = 'direction-positive'
                dir_color = '#26a69a'
                dir_symbol = '▲'
            elif direction == 'negative':
                dir_class = 'direction-negative'
                dir_color = '#ef5350'
                dir_symbol = '▼'
            else:
                dir_class = 'direction-neutral'
                dir_color = '#787b86'
                dir_symbol = '●'
            
            # Impact score styling
            impact = event.get('impact_score', 50)
            if impact >= 75:
                impact_badge_class = 'high'
                impact_color = '#26a69a'
            elif impact >= 50:
                impact_badge_class = 'medium'
                impact_color = '#ff9800'
            else:
                impact_badge_class = 'low'
                impact_color = '#ef5350'
            
            confidence = event.get('confidence', 0.5)
            
            # Event card with TradingView styling
            st.markdown(f"""
                <div class='event-card'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                        <div style='flex: 1;'>
                            <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 8px;'>
                                <span style='font-weight: 700; font-size: 16px; color: #d1d4dc;'>{event['ticker']}</span>
                                <span style='color: {dir_color}; font-weight: 600;'>{dir_symbol}</span>
                                <span style='background-color: #2a2e39; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #787b86;'>
                                    {event['event_type'].replace('_', ' ').title()}
                                </span>
                                {f"<span style='color: #5d606b; font-size: 12px;'>{event.get('sector', '')}</span>" if event.get('sector') else ''}
                            </div>
                            <div style='color: #d1d4dc; font-size: 14px; margin-bottom: 4px;'>{event['title'][:100]}</div>
                            <div style='color: #5d606b; font-size: 12px;'>{date_str}</div>
                        </div>
                        <div style='text-align: center; min-width: 70px;'>
                            <div class='impact-badge {impact_badge_class}' style='margin-bottom: 4px;'>
                                {impact}
                            </div>
                            <div style='font-size: 10px; color: #5d606b;'>{confidence:.0%} conf</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Expander for details
            with st.expander(f"Details: {event['ticker']} - {event['title'][:50]}"):
                col_detail1, col_detail2 = st.columns([2, 1])
                
                with col_detail1:
                    st.markdown(f"**Company:** {event['company_name']}")
                    st.markdown(f"**Source:** {event['source']}")
                    if event.get('description'):
                        st.markdown(f"**Description:** {event['description']}")
                    if event.get('source_url'):
                        st.markdown(f"[View Original Document]({event['source_url']})")
                
                with col_detail2:
                    if event.get('rationale'):
                        st.info(f"**Impact Rationale:** {event['rationale']}")
    else:
        st.markdown("""
            <div style='text-align: center; padding: 40px; color: #787b86;'>
                <div style='font-size: 48px; margin-bottom: 16px;'>📊</div>
                <div style='font-size: 16px;'>No events match your filters</div>
                <div style='font-size: 14px; margin-top: 8px;'>Adjust filter criteria or check back later</div>
            </div>
        """, unsafe_allow_html=True)

# ============================================================================
# COMPANIES PAGE
# ============================================================================

if st.session_state.current_page == "Companies":
    st.markdown("## Company Coverage")
    st.caption("Tracked companies and their upcoming events")
    
    companies = dm.get_companies(tracked_only=True, with_event_counts=True)
    
    st.markdown(f"**{len(companies)} companies tracked**")
    
    # Display companies in table
    for company in companies:
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        
        with col1:
            st.markdown(f"**{company['ticker']}**")
        
        with col2:
            st.text(company['name'])
        
        with col3:
            if company.get('sector'):
                st.text(company['sector'])
        
        with col4:
            event_count = company.get('event_count', 0)
            st.text(f"{event_count} events")
        
        # Show upcoming events for this company
        with st.expander(f"View events for {company['ticker']}"):
            company_events = dm.get_events(ticker=company['ticker'], upcoming_only=True, limit=10)
            
            if company_events:
                for event in company_events:
                    st.markdown(f"**{event['date'].strftime('%b %d, %Y')}** - {event['title']}")
                    st.caption(f"Impact: {event['impact_score']} | Direction: {event.get('direction', 'neutral')}")
            else:
                st.info("No upcoming events")
        
        st.markdown("---")

# ============================================================================
# WATCHLIST PAGE
# ============================================================================

if st.session_state.current_page == "Watchlist":
    st.markdown("## Your Watchlist")
    st.caption("Track specific tickers for personalized event monitoring")
    
    # Add to watchlist
    with st.form("add_watchlist"):
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            new_ticker = st.text_input("Ticker Symbol", placeholder="AAPL").upper()
        
        with col2:
            notes = st.text_input("Notes (optional)", placeholder="Why are you tracking this?")
        
        with col3:
            st.write("")  # Spacing
            add_submitted = st.form_submit_button("Add", type="primary", use_container_width=True)
        
        if add_submitted and new_ticker:
            dm.add_to_watchlist(ticker=new_ticker, user_id=st.session_state.user_id, notes=notes)
            st.success(f"Added {new_ticker} to watchlist")
            st.rerun()
    
    # Show watchlist
    watchlist = dm.get_watchlist(user_id=st.session_state.user_id)
    
    if watchlist:
        st.markdown(f"**{len(watchlist)} tickers in watchlist**")
        
        for item in watchlist:
            col1, col2, col3 = st.columns([1, 4, 1])
            
            with col1:
                st.markdown(f"**{item['ticker']}**")
            
            with col2:
                if item.get('notes'):
                    st.caption(item['notes'])
                
                # Get upcoming events for this ticker
                upcoming_events = dm.get_events(ticker=item['ticker'], upcoming_only=True, limit=3)
                if upcoming_events:
                    st.caption(f"Next event: {upcoming_events[0]['title'][:60]} ({upcoming_events[0]['date'].strftime('%b %d')})")
            
            with col3:
                if st.button("Remove", key=f"remove_{item['ticker']}"):
                    dm.remove_from_watchlist(ticker=item['ticker'], user_id=st.session_state.user_id)
                    st.rerun()
            
            st.markdown("---")
    else:
        st.info("Your watchlist is empty. Add tickers above to start tracking events.")

# ============================================================================
# EARNINGS PAGE
# ============================================================================

if st.session_state.current_page == "Earnings":
    st.markdown("## Earnings Tracker")
    st.caption("Track your portfolio and project earnings/losses based on upcoming events")
    
    ticker_input = st.text_input("Enter Stock Ticker", placeholder="e.g., AAPL", key="earnings_ticker").upper()
    
    if ticker_input:
        try:
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
                    
                    upcoming_events = dm.get_events(ticker=ticker_input, upcoming_only=True)
                    
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
                            date_str = event['date'].strftime('%Y-%m-%d %H:%M') if isinstance(event['date'], datetime) else str(event['date'])
                            st.caption(f"{event['event_type']} - {date_str}")
                        
                        with col2:
                            impact_score = event.get('impact_score', 50)
                            impact_class = 'low' if impact_score < 50 else ('medium' if impact_score < 75 else 'high')
                            st.markdown(f"""
                                <div class='impact-badge {impact_class}' style='width: 100%; padding: 8px 12px;'>
                                    <div style='font-size: 11px; opacity: 0.8;'>Impact</div>
                                    <div style='font-size: 20px;'>{impact_score}</div>
                                </div>
                            """, unsafe_allow_html=True)
                        
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
                    st.info(f"No upcoming events tracked for {ticker_input}.")
            else:
                st.error(f"Could not fetch data for ticker {ticker_input}. Please check if the ticker is valid.")
        
        except Exception as e:
            st.error(f"Error fetching stock data: {str(e)}")
    else:
        st.info("Enter a stock ticker above to view earnings projections and track your portfolio")

# ============================================================================
# SCANNER STATUS PAGE
# ============================================================================

if st.session_state.current_page == "Scanner Status":
    st.markdown("## Scanner Status")
    st.caption("Real-time status of automated event ingestion scanners")
    
    scanner_status = dm.get_scanner_status()
    
    col1, col2, col3 = st.columns(3)
    
    for i, (scanner_name, status) in enumerate(scanner_status.items()):
        with [col1, col2, col3][i % 3]:
            st.markdown(f"### {scanner_name}")
            
            if status['last_run']:
                time_ago = datetime.utcnow() - status['last_run']
                hours_ago = int(time_ago.total_seconds() / 3600)
                st.metric("Last Run", f"{hours_ago}h ago")
            else:
                st.metric("Last Run", "Never")
            
            level = status.get('last_level', 'info')
            if level == 'error':
                st.error(f"❌ {status['last_message']}")
            elif level == 'warning':
                st.warning(f"⚠️ {status['last_message']}")
            else:
                st.success(f"✓ {status['last_message']}")
    
    st.markdown("---")
    
    # Manual scan button
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Run Manual Scan Now", type="primary", use_container_width=True):
            with st.spinner("Scanning SEC EDGAR, FDA, and company releases..."):
                try:
                    scanner_service.run_manual_scan()
                    st.success("Manual scan completed! Check Recent Logs below for details.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Scan error: {str(e)}")
    
    with col2:
        st.caption("Manually trigger a full scan of SEC filings, FDA announcements, and press releases for all tracked companies")
    
    # Recent logs
    st.markdown("---")
    st.markdown("### Recent Scanner Logs")
    
    logs = dm.get_scanner_logs(limit=20)
    
    for log in logs:
        time_str = log['timestamp'].strftime('%H:%M:%S')
        
        if log['level'] == 'error':
            st.error(f"[{time_str}] **{log['scanner']}**: {log['message']}")
        elif log['level'] == 'warning':
            st.warning(f"[{time_str}] **{log['scanner']}**: {log['message']}")
        else:
            st.info(f"[{time_str}] **{log['scanner']}**: {log['message']}")

# ============================================================================
# MODELING PAGE - Topological Stock Analysis
# ============================================================================

if st.session_state.current_page == "Modeling":
    import plotly.graph_objects as go
    import numpy as np
    import requests
    
    st.markdown("## Topological Stock Modeling")
    st.caption("Analyze stock patterns using persistent homology and Takens embeddings")
    
    # Initialize session state for modeling
    if 'modeling_ticker' not in st.session_state:
        st.session_state.modeling_ticker = 'AAPL'
    if 'modeling_results' not in st.session_state:
        st.session_state.modeling_results = None
    if 'backtest_results' not in st.session_state:
        st.session_state.backtest_results = None
    
    # --- Control Sidebar ---
    with st.sidebar:
        st.markdown("### Parameters")
        
        ticker_input = st.text_input("Ticker Symbol", value=st.session_state.modeling_ticker, max_chars=10).upper()
        
        st.markdown("#### Takens Embedding")
        embedding_dim = st.slider("Embedding Dimension (m)", min_value=2, max_value=8, value=3,
                                  help="Higher dimensions capture more complex dynamics")
        delay = st.slider("Time Delay (τ)", min_value=1, max_value=10, value=2,
                         help="Spacing between coordinates in the embedding")
        lookback_days = st.slider("Lookback Days", min_value=20, max_value=180, value=60,
                                  help="Days of price history to analyze")
        
        end_date = st.date_input("Analysis Date", value=datetime.now().date())
        
        analyze_btn = st.button("Analyze Topology", type="primary", use_container_width=True)
    
    # Three tabs for different analysis modes
    tab1, tab2, tab3 = st.tabs(["Shape Explorer", "Topology Analyzer", "Strategy Lab"])
    
    # --- Shape Explorer Tab ---
    with tab1:
        st.markdown("### Price Pattern Geometry")
        st.caption("Visualize the attractor structure of price dynamics via Takens delay embedding")
        
        if analyze_btn or st.session_state.modeling_results:
            if analyze_btn:
                with st.spinner("Computing topological features..."):
                    try:
                        st.session_state.modeling_results = _compute_topology_local(
                            ticker_input, end_date, lookback_days, embedding_dim, delay
                        )
                        st.session_state.modeling_ticker = ticker_input
                    except Exception as e:
                        st.error(f"Error computing topology: {str(e)}")
                        st.session_state.modeling_results = {'has_data': False, 'error_message': str(e)}
            
            results = st.session_state.modeling_results
            
            if results and results.get('has_data', False):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # 3D Takens Embedding Plot
                    embedding_points = results.get('embedding_points', [])
                    
                    if embedding_points and len(embedding_points) > 0:
                        points = np.array(embedding_points)
                        
                        if points.shape[1] >= 3:
                            fig = go.Figure(data=[go.Scatter3d(
                                x=points[:, 0],
                                y=points[:, 1],
                                z=points[:, 2],
                                mode='markers+lines',
                                marker=dict(
                                    size=3,
                                    color=np.arange(len(points)),
                                    colorscale='Viridis',
                                    opacity=0.8
                                ),
                                line=dict(color='rgba(100,100,100,0.3)', width=1),
                                hovertemplate='x: %{x:.3f}<br>y: %{y:.3f}<br>z: %{z:.3f}<extra></extra>'
                            )])
                            
                            fig.update_layout(
                                title=f"Takens Embedding - {results.get('ticker', ticker_input)}",
                                scene=dict(
                                    xaxis_title='x(t)',
                                    yaxis_title=f'x(t+{delay})',
                                    zaxis_title=f'x(t+{2*delay})',
                                    bgcolor='rgb(20,20,30)'
                                ),
                                paper_bgcolor='rgb(20,20,30)',
                                font=dict(color='white'),
                                height=500,
                                margin=dict(l=0, r=0, t=40, b=0)
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Need at least 3D embedding for visualization")
                    else:
                        st.warning("No embedding points available")
                
                with col2:
                    # Price chart with returns
                    prices = results.get('prices', [])
                    dates = results.get('dates', [])
                    
                    if prices and dates:
                        fig = go.Figure()
                        
                        fig.add_trace(go.Scatter(
                            x=dates,
                            y=prices,
                            mode='lines',
                            name='Price',
                            line=dict(color='#00d4aa', width=2)
                        ))
                        
                        fig.update_layout(
                            title=f"Price History - {results.get('ticker', ticker_input)}",
                            xaxis_title='Date',
                            yaxis_title='Price ($)',
                            paper_bgcolor='rgb(20,20,30)',
                            plot_bgcolor='rgb(20,20,30)',
                            font=dict(color='white'),
                            height=500,
                            xaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                            yaxis=dict(gridcolor='rgba(100,100,100,0.2)')
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                
                # Feature summary cards
                features = results.get('features', {})
                
                st.markdown("### Topological Features")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Connected Components", int(features.get('betti0_count', 0)),
                             help="Number of distinct clusters in the embedding")
                
                with col2:
                    st.metric("Loops Detected", int(features.get('betti1_count', 0)),
                             help="Cyclical patterns in price dynamics")
                
                with col3:
                    st.metric("Persistence Entropy", f"{features.get('persistence_entropy', 0):.3f}",
                             help="Complexity measure (0-1, higher = more complex)")
                
                with col4:
                    st.metric("Topological Complexity", f"{features.get('topological_complexity', 0):.1f}",
                             help="Composite complexity score")
            
            elif results and results.get('error_message'):
                st.error(f"Analysis failed: {results['error_message']}")
            else:
                st.info("Enter a ticker and click 'Analyze Topology' to begin")
        else:
            st.info("Enter a ticker symbol in the sidebar and click 'Analyze Topology' to visualize the stock's geometric structure")
            
            # Show example interpretation
            with st.expander("What is Takens Embedding?"):
                st.markdown("""
                **Takens delay embedding** reconstructs the hidden dynamics of a system from observed time series data.
                
                Given price returns x(t), we create vectors:
                - **[x(t), x(t+τ), x(t+2τ), ...]**
                
                Where τ is the time delay between observations.
                
                This reveals the **attractor geometry** - the underlying structure governing price movements:
                - **Clusters** indicate distinct market regimes
                - **Loops** reveal cyclical patterns
                - **Complex structures** suggest chaotic dynamics
                """)
    
    # --- Topology Analyzer Tab ---
    with tab2:
        st.markdown("### Persistence Diagrams")
        st.caption("Track birth and death of topological features across scales")
        
        results = st.session_state.modeling_results
        
        if results and results.get('has_data', False):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Persistence diagram
                h0_diagram = results.get('persistence_diagram_h0', [])
                h1_diagram = results.get('persistence_diagram_h1', [])
                
                fig = go.Figure()
                
                # H0 points (connected components)
                if h0_diagram:
                    h0_array = np.array(h0_diagram)
                    fig.add_trace(go.Scatter(
                        x=h0_array[:, 0],
                        y=h0_array[:, 1],
                        mode='markers',
                        name='H0 (Components)',
                        marker=dict(color='#ff6b6b', size=8, symbol='circle'),
                        hovertemplate='Birth: %{x:.3f}<br>Death: %{y:.3f}<extra>H0</extra>'
                    ))
                
                # H1 points (loops)
                if h1_diagram:
                    h1_array = np.array(h1_diagram)
                    fig.add_trace(go.Scatter(
                        x=h1_array[:, 0],
                        y=h1_array[:, 1],
                        mode='markers',
                        name='H1 (Loops)',
                        marker=dict(color='#4ecdc4', size=8, symbol='diamond'),
                        hovertemplate='Birth: %{x:.3f}<br>Death: %{y:.3f}<extra>H1</extra>'
                    ))
                
                # Diagonal line
                if h0_diagram or h1_diagram:
                    all_points = h0_diagram + h1_diagram
                    max_val = max(max(p[1] for p in all_points), max(p[0] for p in all_points)) if all_points else 1
                    fig.add_trace(go.Scatter(
                        x=[0, max_val],
                        y=[0, max_val],
                        mode='lines',
                        name='Diagonal',
                        line=dict(color='gray', dash='dash', width=1)
                    ))
                
                fig.update_layout(
                    title="Persistence Diagram",
                    xaxis_title="Birth",
                    yaxis_title="Death",
                    paper_bgcolor='rgb(20,20,30)',
                    plot_bgcolor='rgb(20,20,30)',
                    font=dict(color='white'),
                    height=400,
                    xaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                    yaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                    legend=dict(x=0.02, y=0.98)
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Betti curves
                betti_scales = results.get('betti_curve_scales', [])
                betti_h0 = results.get('betti_curve_h0', [])
                betti_h1 = results.get('betti_curve_h1', [])
                
                if betti_scales:
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=betti_scales,
                        y=betti_h0,
                        mode='lines',
                        name='β₀ (Components)',
                        line=dict(color='#ff6b6b', width=2)
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=betti_scales,
                        y=betti_h1,
                        mode='lines',
                        name='β₁ (Loops)',
                        line=dict(color='#4ecdc4', width=2)
                    ))
                    
                    fig.update_layout(
                        title="Betti Curves",
                        xaxis_title="Filtration Scale (ε)",
                        yaxis_title="Betti Number",
                        paper_bgcolor='rgb(20,20,30)',
                        plot_bgcolor='rgb(20,20,30)',
                        font=dict(color='white'),
                        height=400,
                        xaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                        yaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                        legend=dict(x=0.02, y=0.98)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Betti curves not available")
            
            # Feature details table
            features = results.get('features', {})
            
            st.markdown("### Feature Details")
            
            feature_data = []
            for name, value in features.items():
                description = {
                    'betti0_count': 'Connected components in embedding',
                    'betti1_count': 'Loops/cycles detected',
                    'max_lifetime_h0': 'Longest-persisting component',
                    'max_lifetime_h1': 'Longest-persisting loop',
                    'mean_lifetime_h0': 'Average component lifetime',
                    'mean_lifetime_h1': 'Average loop lifetime',
                    'total_persistence_h0': 'Total H0 persistence',
                    'total_persistence_h1': 'Total H1 persistence',
                    'persistence_entropy': 'Normalized entropy (0-1)',
                    'betti_curve_h0_mean': 'Mean of β₀ curve',
                    'betti_curve_h1_mean': 'Mean of β₁ curve',
                    'topological_complexity': 'Composite complexity score'
                }.get(name, '')
                
                feature_data.append({
                    'Feature': name.replace('_', ' ').title(),
                    'Value': f"{value:.4f}" if isinstance(value, float) else str(value),
                    'Description': description
                })
            
            if feature_data:
                st.dataframe(pd.DataFrame(feature_data), use_container_width=True, hide_index=True)
        else:
            st.info("Run topology analysis first to see persistence diagrams and Betti curves")
    
    # --- Strategy Lab Tab ---
    with tab3:
        st.markdown("### Topology-Based Trading Strategy")
        st.caption("Build and backtest strategies using topological features as signals")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### Entry Conditions")
            
            use_betti1 = st.checkbox("Use Loop Count (β₁)", value=True)
            if use_betti1:
                betti1_operator = st.selectbox("Condition", [">", ">=", "<", "<="], key="betti1_op")
                betti1_threshold = st.number_input("Threshold", min_value=0, max_value=200, value=10, key="betti1_val")
            
            use_entropy = st.checkbox("Use Persistence Entropy", value=False)
            if use_entropy:
                entropy_operator = st.selectbox("Condition", [">", ">=", "<", "<="], key="entropy_op")
                entropy_threshold = st.number_input("Threshold", min_value=0.0, max_value=1.0, value=0.7, step=0.05, key="entropy_val")
            
            use_complexity = st.checkbox("Use Topological Complexity", value=False)
            if use_complexity:
                complexity_operator = st.selectbox("Condition", [">", ">=", "<", "<="], key="complexity_op")
                complexity_threshold = st.number_input("Threshold", min_value=0.0, max_value=500.0, value=50.0, step=5.0, key="complexity_val")
            
            st.markdown("#### Exit Conditions")
            
            max_hold_days = st.number_input("Max Holding Days", min_value=1, max_value=60, value=10)
            stop_loss = st.number_input("Stop Loss (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
            take_profit = st.number_input("Take Profit (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
            
            st.markdown("#### Backtest Settings")
            
            bt_start = st.date_input("Start Date", value=datetime.now().date() - timedelta(days=365), key="bt_start")
            bt_end = st.date_input("End Date", value=datetime.now().date(), key="bt_end")
            initial_capital = st.number_input("Initial Capital ($)", min_value=1000, max_value=1000000, value=10000, step=1000)
            
            run_backtest_btn = st.button("Run Backtest", type="primary", use_container_width=True)
        
        with col2:
            if run_backtest_btn:
                # Build entry conditions
                entry_conditions = {}
                if use_betti1:
                    entry_conditions['betti1_count'] = {'operator': betti1_operator, 'value': betti1_threshold}
                if use_entropy:
                    entry_conditions['persistence_entropy'] = {'operator': entropy_operator, 'value': entropy_threshold}
                if use_complexity:
                    entry_conditions['topological_complexity'] = {'operator': complexity_operator, 'value': complexity_threshold}
                
                if not entry_conditions:
                    st.warning("Please select at least one entry condition")
                else:
                    with st.spinner("Running topology-based backtest..."):
                        try:
                            backtest_result = _run_local_backtest(
                                ticker=st.session_state.modeling_ticker,
                                start_date=bt_start,
                                end_date=bt_end,
                                embedding_dim=embedding_dim,
                                delay=delay,
                                lookback_days=lookback_days,
                                entry_conditions=entry_conditions,
                                max_holding_days=max_hold_days,
                                stop_loss_pct=stop_loss,
                                take_profit_pct=take_profit,
                                initial_capital=initial_capital
                            )
                            
                            st.session_state.backtest_results = backtest_result
                        except Exception as e:
                            st.error(f"Backtest failed: {str(e)}")
            
            # Display backtest results
            bt_results = st.session_state.backtest_results
            
            if bt_results:
                st.markdown("### Backtest Results")
                
                col_a, col_b, col_c, col_d = st.columns(4)
                
                with col_a:
                    st.metric("Total Return", f"{bt_results.get('total_return_pct', 0):.1f}%")
                
                with col_b:
                    st.metric("Win Rate", f"{bt_results.get('win_rate', 0):.1f}%")
                
                with col_c:
                    sharpe = bt_results.get('sharpe_ratio')
                    st.metric("Sharpe Ratio", f"{sharpe:.2f}" if sharpe else "N/A")
                
                with col_d:
                    st.metric("Max Drawdown", f"{bt_results.get('max_drawdown_pct', 0):.1f}%")
                
                # Equity curve
                equity_curve = bt_results.get('equity_curve', [])
                
                if equity_curve:
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=[e['date'] for e in equity_curve],
                        y=[e['equity'] for e in equity_curve],
                        mode='lines',
                        name='Portfolio Value',
                        line=dict(color='#00d4aa', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(0,212,170,0.1)'
                    ))
                    
                    fig.update_layout(
                        title="Equity Curve",
                        xaxis_title='Date',
                        yaxis_title='Portfolio Value ($)',
                        paper_bgcolor='rgb(20,20,30)',
                        plot_bgcolor='rgb(20,20,30)',
                        font=dict(color='white'),
                        height=350,
                        xaxis=dict(gridcolor='rgba(100,100,100,0.2)'),
                        yaxis=dict(gridcolor='rgba(100,100,100,0.2)')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                # Trade list
                trades = bt_results.get('trades', [])
                
                if trades:
                    st.markdown("### Trade History")
                    
                    trade_df = pd.DataFrame([{
                        'Entry': t.get('entry_date', ''),
                        'Exit': t.get('exit_date', ''),
                        'Entry Price': f"${t.get('entry_price', 0):.2f}",
                        'Exit Price': f"${t.get('exit_price', 0):.2f}",
                        'Return': f"{t.get('return_pct', 0):.1f}%",
                        'Days Held': t.get('holding_days', 0),
                        'Exit Reason': t.get('exit_reason', '')
                    } for t in trades])
                    
                    st.dataframe(trade_df, use_container_width=True, hide_index=True)
                
                st.markdown(f"**Total Trades:** {bt_results.get('total_trades', 0)} | "
                           f"**Winning:** {bt_results.get('winning_trades', 0)} | "
                           f"**Losing:** {bt_results.get('losing_trades', 0)}")
            else:
                st.info("Configure your strategy conditions and click 'Run Backtest' to see results")


def _compute_topology_local(ticker: str, end_date, lookback_days: int, embedding_dim: int, delay: int) -> dict:
    """Compute topology features locally without API."""
    try:
        import yfinance as yf
        
        start = end_date - timedelta(days=lookback_days + 30)
        data = yf.download(ticker, start=start.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        
        if data.empty:
            return {'has_data': False, 'error_message': f'No data for {ticker}'}
        
        if 'Adj Close' in data.columns:
            prices = data['Adj Close'].values
        elif 'Close' in data.columns:
            prices = data['Close'].values
        else:
            prices = data.iloc[:, 0].values
        
        if hasattr(prices, 'flatten'):
            prices = prices.flatten()
        
        dates = [d.strftime('%Y-%m-%d') for d in data.index]
        
        log_prices = np.log(prices)
        returns = np.diff(log_prices)
        
        returns_std = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)
        
        n = len(returns_std)
        n_points = n - (embedding_dim - 1) * delay
        
        if n_points < 5:
            return {'has_data': False, 'error_message': 'Insufficient data for embedding'}
        
        embedding_points = []
        for i in range(n_points):
            point = [returns_std[i + j * delay] for j in range(embedding_dim)]
            embedding_points.append(point)
        
        h0_diagram = []
        h1_diagram = []
        betti_h0 = []
        betti_h1 = []
        betti_scales = []
        
        try:
            import ripser
            
            points_array = np.array(embedding_points)
            result = ripser.ripser(points_array, maxdim=1, thresh=2.0)
            dgms = result['dgms']
            
            if len(dgms) > 0:
                for birth, death in dgms[0]:
                    if not np.isinf(death) and death - birth > 0.01:
                        h0_diagram.append([float(birth), float(death)])
            
            if len(dgms) > 1:
                for birth, death in dgms[1]:
                    if not np.isinf(death) and death - birth > 0.01:
                        h1_diagram.append([float(birth), float(death)])
            
            all_points = h0_diagram + h1_diagram
            if all_points:
                min_b = min(p[0] for p in all_points)
                max_d = max(p[1] for p in all_points)
                betti_scales = np.linspace(min_b, max_d, 50).tolist()
                
                for scale in betti_scales:
                    betti_h0.append(sum(1 for p in h0_diagram if p[0] <= scale < p[1]))
                    betti_h1.append(sum(1 for p in h1_diagram if p[0] <= scale < p[1]))
        except ImportError:
            pass
        
        h0_lifetimes = [p[1] - p[0] for p in h0_diagram]
        h1_lifetimes = [p[1] - p[0] for p in h1_diagram]
        all_lifetimes = h0_lifetimes + h1_lifetimes
        
        entropy = 0.0
        if len(all_lifetimes) >= 2:
            total = sum(all_lifetimes)
            if total > 0:
                probs = [l / total for l in all_lifetimes]
                entropy = -sum(p * np.log(p + 1e-10) for p in probs) / np.log(len(all_lifetimes))
        
        features = {
            'betti0_count': len(h0_lifetimes),
            'betti1_count': len(h1_lifetimes),
            'max_lifetime_h0': max(h0_lifetimes) if h0_lifetimes else 0.0,
            'max_lifetime_h1': max(h1_lifetimes) if h1_lifetimes else 0.0,
            'mean_lifetime_h0': np.mean(h0_lifetimes) if h0_lifetimes else 0.0,
            'mean_lifetime_h1': np.mean(h1_lifetimes) if h1_lifetimes else 0.0,
            'total_persistence_h0': sum(h0_lifetimes),
            'total_persistence_h1': sum(h1_lifetimes),
            'persistence_entropy': entropy,
            'betti_curve_h0_mean': np.mean(betti_h0) if betti_h0 else 0.0,
            'betti_curve_h1_mean': np.mean(betti_h1) if betti_h1 else 0.0,
            'topological_complexity': len(h1_lifetimes) * 2.0 + entropy + sum(h1_lifetimes)
        }
        
        return {
            'ticker': ticker,
            'analysis_date': end_date.strftime('%Y-%m-%d'),
            'lookback_days': lookback_days,
            'embedding_dim': embedding_dim,
            'delay': delay,
            'embedding_points': embedding_points,
            'prices': prices[-lookback_days:].tolist(),
            'dates': dates[-lookback_days:],
            'returns': returns[-lookback_days+1:].tolist(),
            'persistence_diagram_h0': h0_diagram,
            'persistence_diagram_h1': h1_diagram,
            'betti_curve_scales': betti_scales,
            'betti_curve_h0': betti_h0,
            'betti_curve_h1': betti_h1,
            'features': features,
            'has_data': True
        }
    except Exception as e:
        return {'has_data': False, 'error_message': str(e)}


def _run_local_backtest(ticker: str, start_date, end_date, embedding_dim: int, delay: int,
                        lookback_days: int, entry_conditions: dict, max_holding_days: int,
                        stop_loss_pct: float, take_profit_pct: float, initial_capital: float) -> dict:
    """Run a local backtest using topology features."""
    import yfinance as yf
    
    buffer_start = start_date - timedelta(days=lookback_days + 30)
    data = yf.download(ticker, start=buffer_start.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    
    if data.empty:
        return {'error': f'No data for {ticker}'}
    
    if 'Adj Close' in data.columns:
        prices = data['Adj Close'].values
    elif 'Close' in data.columns:
        prices = data['Close'].values
    else:
        prices = data.iloc[:, 0].values
    
    if hasattr(prices, 'flatten'):
        prices = prices.flatten()
    
    dates = [d.strftime('%Y-%m-%d') for d in data.index]
    log_prices = np.log(prices)
    returns = np.diff(log_prices)
    
    try:
        import ripser
        has_ripser = True
    except ImportError:
        has_ripser = False
    
    trades = []
    equity_curve = []
    capital = initial_capital
    position = None
    
    for i in range(lookback_days, len(prices)):
        current_date = dates[i]
        current_price = prices[i]
        
        pos_value = position['shares'] * current_price if position else 0
        equity_curve.append({
            'date': current_date,
            'equity': capital + pos_value,
            'in_position': position is not None
        })
        
        if position:
            days_held = (datetime.strptime(current_date, '%Y-%m-%d') - 
                        datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
            
            exit_reason = None
            if days_held >= max_holding_days:
                exit_reason = 'max_holding_days'
            elif pnl_pct <= -stop_loss_pct:
                exit_reason = 'stop_loss'
            elif pnl_pct >= take_profit_pct:
                exit_reason = 'take_profit'
            
            if exit_reason:
                profit_loss = position['shares'] * (current_price - position['entry_price'])
                capital += position['shares'] * current_price
                
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': current_date,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'return_pct': pnl_pct,
                    'profit_loss': profit_loss,
                    'holding_days': days_held,
                    'entry_reason': position.get('entry_reason', ''),
                    'exit_reason': exit_reason
                })
                position = None
        else:
            lookback_returns = returns[i - lookback_days:i]
            
            if len(lookback_returns) >= lookback_days and has_ripser:
                returns_std = (lookback_returns - np.mean(lookback_returns)) / (np.std(lookback_returns) + 1e-8)
                
                n = len(returns_std)
                n_points = n - (embedding_dim - 1) * delay
                
                if n_points >= 5:
                    embedding = np.array([[returns_std[j + k * delay] for k in range(embedding_dim)]
                                         for j in range(n_points)])
                    
                    result = ripser.ripser(embedding, maxdim=1, thresh=2.0)
                    dgms = result['dgms']
                    
                    h1_lifetimes = []
                    if len(dgms) > 1:
                        for birth, death in dgms[1]:
                            if not np.isinf(death) and death - birth > 0.01:
                                h1_lifetimes.append(death - birth)
                    
                    h0_lifetimes = []
                    if len(dgms) > 0:
                        for birth, death in dgms[0]:
                            if not np.isinf(death) and death - birth > 0.01:
                                h0_lifetimes.append(death - birth)
                    
                    all_lifetimes = h0_lifetimes + h1_lifetimes
                    entropy = 0.0
                    if len(all_lifetimes) >= 2:
                        total = sum(all_lifetimes)
                        if total > 0:
                            probs = [l / total for l in all_lifetimes]
                            entropy = -sum(p * np.log(p + 1e-10) for p in probs) / np.log(len(all_lifetimes))
                    
                    features = {
                        'betti1_count': len(h1_lifetimes),
                        'persistence_entropy': entropy,
                        'topological_complexity': len(h1_lifetimes) * 2.0 + entropy + sum(h1_lifetimes)
                    }
                    
                    should_enter = True
                    for feat_name, cond in entry_conditions.items():
                        if feat_name in features:
                            val = features[feat_name]
                            op = cond['operator']
                            thresh = cond['value']
                            
                            if op == '>' and val <= thresh:
                                should_enter = False
                            elif op == '>=' and val < thresh:
                                should_enter = False
                            elif op == '<' and val >= thresh:
                                should_enter = False
                            elif op == '<=' and val > thresh:
                                should_enter = False
                    
                    if should_enter:
                        shares = capital / current_price
                        capital = 0
                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'shares': shares,
                            'entry_reason': 'topology_signal'
                        }
    
    if position:
        final_price = prices[-1]
        pnl_pct = (final_price - position['entry_price']) / position['entry_price'] * 100
        days_held = (datetime.strptime(dates[-1], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
        capital += position['shares'] * final_price
        
        trades.append({
            'entry_date': position['entry_date'],
            'exit_date': dates[-1],
            'entry_price': position['entry_price'],
            'exit_price': final_price,
            'return_pct': pnl_pct,
            'profit_loss': position['shares'] * (final_price - position['entry_price']),
            'holding_days': days_held,
            'entry_reason': position.get('entry_reason', ''),
            'exit_reason': 'end_of_period'
        })
    
    winning = [t for t in trades if t['return_pct'] > 0]
    losing = [t for t in trades if t['return_pct'] <= 0]
    
    total_return_pct = (capital - initial_capital) / initial_capital * 100
    
    max_dd = 0.0
    peak = equity_curve[0]['equity'] if equity_curve else initial_capital
    for e in equity_curve:
        if e['equity'] > peak:
            peak = e['equity']
        dd = (peak - e['equity']) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    sharpe = None
    if len(trades) >= 2:
        rets = [t['return_pct'] / 100 for t in trades]
        avg_ret = np.mean(rets)
        std_ret = np.std(rets)
        if std_ret > 0.0001:
            avg_hold = np.mean([t['holding_days'] for t in trades])
            annual_factor = 252 / avg_hold if avg_hold > 0 else 252
            sharpe = round((avg_ret * annual_factor - 0.02) / (std_ret * np.sqrt(annual_factor)), 2)
    
    return {
        'ticker': ticker,
        'start_date': str(start_date),
        'end_date': str(end_date),
        'total_trades': len(trades),
        'winning_trades': len(winning),
        'losing_trades': len(losing),
        'win_rate': len(winning) / len(trades) * 100 if trades else 0,
        'total_return_pct': total_return_pct,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_dd,
        'avg_holding_days': np.mean([t['holding_days'] for t in trades]) if trades else 0,
        'trades': trades,
        'equity_curve': equity_curve,
        'initial_capital': initial_capital,
        'final_capital': capital
    }


# ============================================================================
# ACCOUNT PAGE
# ============================================================================

if st.session_state.current_page == "Account":
    st.markdown("## Account")
    
    st.markdown(f"**Email:** {st.session_state.user_email or 'N/A'}")
    st.markdown(f"**Phone:** {st.session_state.user_phone or 'N/A'}")
    st.markdown(f"**Admin:** {'Yes' if user_is_admin() else 'No'}")

# ============================================================================
# COMPLIANCE FOOTER
# ============================================================================

st.markdown("---")
st.caption("**Information only. Not investment advice. No performance guarantees. Always verify with original filings.**")
