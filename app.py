import streamlit as st
import psycopg2
import os
from datetime import datetime

st.set_page_config(
    page_title="Satta King",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def get_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name, game_time, yesterday_result, today_result FROM games WHERE is_active = true ORDER BY display_order ASC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        return games
    except:
        return []

games = get_games()
current_date = datetime.now().strftime("%d-%m-%Y")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
    }
    
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    
    .stMainBlockContainer {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 5px !important;
        padding-right: 5px !important;
    }
    
    @media (min-width: 768px) {
        .stMainBlockContainer {
            padding-left: 10% !important;
            padding-right: 10% !important;
        }
    }
    
    @media (min-width: 1200px) {
        .stMainBlockContainer {
            padding-left: 15% !important;
            padding-right: 15% !important;
        }
    }
    
    @media (min-width: 1600px) {
        .stMainBlockContainer {
            padding-left: 20% !important;
            padding-right: 20% !important;
        }
    }
    
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    .header-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px 0;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    
    .site-title {
        color: #fff;
        font-size: 36px;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .site-subtitle {
        color: rgba(255,255,255,0.9);
        font-size: 14px;
        margin-top: 8px;
    }
    
    .nav-section {
        background: #1e1e30;
        padding: 12px 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .nav-menu {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        padding: 0 20px;
    }
    
    .nav-item {
        color: #b0b0c0;
        padding: 8px 20px;
        border-radius: 20px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s;
        text-decoration: none;
    }
    
    .nav-item:hover, .nav-item.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
    }
    
    .date-banner {
        background: linear-gradient(135deg, #2d2d44 0%, #3d3d5c 100%);
        padding: 15px;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .date-text {
        color: #00d4ff;
        font-size: 18px;
        font-weight: 600;
    }
    
    .games-section {
        padding: 30px 20px;
        max-width: 1200px;
        margin: 0 auto;
    }
    
    .section-title {
        color: #fff;
        font-size: 24px;
        font-weight: 600;
        text-align: center;
        margin-bottom: 25px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .games-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    .games-table thead {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .games-table th {
        color: #fff;
        padding: 18px 15px;
        font-weight: 600;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-align: center;
    }
    
    .games-table th:first-child {
        width: 180px;
        text-align: left;
    }
    
    .games-table tbody tr {
        background: linear-gradient(135deg, #252540 0%, #2a2a50 100%);
        transition: all 0.3s;
    }
    
    .games-table tbody tr:nth-child(even) {
        background: linear-gradient(135deg, #1e1e35 0%, #252545 100%);
    }
    
    .games-table tbody tr:hover {
        background: linear-gradient(135deg, #3a3a60 0%, #454580 100%);
        transform: scale(1.01);
    }
    
    .games-table td {
        padding: 16px 15px;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
    
    .games-table td:first-child {
        text-align: left;
        width: 180px;
    }
    
    .game-name {
        color: #00d4ff;
        font-weight: 600;
        font-size: 18px;
    }
    
    .record-chart-link {
        color: #667eea;
        font-size: 12px;
        text-decoration: none !important;
        margin-left: 10px;
        font-weight: 500;
    }
    
    .record-chart-link:hover {
        color: #764ba2;
    }
    
    .game-time {
        color: #a0a0b0;
        font-size: 13px;
    }
    
    .result-yesterday {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
        color: #fff;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 18px;
        display: inline-block;
        min-width: 50px;
        box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
    }
    
    .result-today {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: #fff;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 18px;
        display: inline-block;
        min-width: 50px;
        box-shadow: 0 4px 15px rgba(39, 174, 96, 0.3);
    }
    
    .result-pending {
        background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%);
        color: #fff;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 18px;
        display: inline-block;
        min-width: 50px;
    }
    
    .footer-section {
        background: #1e1e30;
        padding: 20px;
        text-align: center;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin-top: 40px;
    }
    
    .footer-links {
        display: flex;
        justify-content: center;
        gap: 20px;
        flex-wrap: wrap;
        margin-bottom: 15px;
    }
    
    .footer-link {
        color: #a0a0b0;
        font-size: 13px;
        text-decoration: none;
        transition: color 0.3s;
    }
    
    .footer-link:hover {
        color: #667eea;
    }
    
    .copyright {
        color: #6a6a7a;
        font-size: 12px;
    }
    
    .no-games {
        text-align: center;
        padding: 60px 20px;
        color: #a0a0b0;
        font-size: 18px;
    }
    
    .refresh-note {
        text-align: center;
        color: #6a6a7a;
        font-size: 12px;
        margin-top: 20px;
    }
    
    @media (max-width: 768px) {
        .site-title {
            font-size: 28px;
        }
        
        .nav-item {
            padding: 6px 12px;
            font-size: 12px;
        }
        
        .games-table th, .games-table td {
            padding: 12px 8px;
            font-size: 12px;
        }
        
        .game-name {
            font-size: 13px;
        }
        
        .result-yesterday, .result-today, .result-pending {
            padding: 6px 10px;
            font-size: 14px;
            min-width: 40px;
        }
        
        .section-title {
            font-size: 18px;
        }
    }
    
    @media (max-width: 480px) {
        .site-title {
            font-size: 24px;
        }
        
        .nav-menu {
            gap: 5px;
        }
        
        .nav-item {
            padding: 5px 10px;
            font-size: 11px;
        }
        
        .games-table th, .games-table td {
            padding: 10px 5px;
            font-size: 11px;
        }
        
        .game-name {
            font-size: 12px;
        }
        
        .game-time {
            font-size: 10px;
        }
        
        .result-yesterday, .result-today, .result-pending {
            padding: 5px 8px;
            font-size: 12px;
            min-width: 35px;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-section">
    <div class="site-title">🎮 Satta King</div>
    <div class="site-subtitle">Live Results & Updates</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="nav-section">
    <div class="nav-menu">
        <span class="nav-item active">Home</span>
        <span class="nav-item">Results</span>
        <span class="nav-item">Chart</span>
        <span class="nav-item">About</span>
        <span class="nav-item">Contact</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="date-banner">
    <span class="date-text">📅 {current_date}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="games-section">
    <div class="section-title">🎯 Today's Results</div>
""", unsafe_allow_html=True)

if games:
    table_html = '<table class="games-table"><thead><tr><th>Game Name</th><th>Yesterday</th><th>Today</th></tr></thead><tbody>'
    
    for game in games:
        name = game[0] or ''
        time_val = game[1] or '--'
        yesterday = game[2] or '--'
        today = game[3] or '--'
        
        yesterday_class = "result-pending" if yesterday == '--' else "result-yesterday"
        today_class = "result-pending" if today == '--' else "result-today"
        
        table_html += f'<tr><td><span class="game-name">{name}</span><br><span class="game-time">{time_val}</span><a href="#" class="record-chart-link">Record Chart</a></td><td><span class="{yesterday_class}">{yesterday}</span></td><td><span class="{today_class}">{today}</span></td></tr>'
    
    table_html += '</tbody></table><div class="refresh-note">Results are updated automatically</div>'
    
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="no-games">
        <p>🎮 No games available</p>
        <p style="font-size: 14px; color: #6a6a7a;">Games will appear here once added from admin panel</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div class="footer-section">
    <div class="footer-links">
        <span class="footer-link">Privacy Policy</span>
        <span class="footer-link">About Us</span>
        <span class="footer-link">Contact</span>
        <span class="footer-link">Disclaimer</span>
    </div>
    <div class="copyright">© 2026 Satta King. All rights reserved.</div>
</div>
""", unsafe_allow_html=True)
