import streamlit as st
import psycopg2
import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
import random

st.set_page_config(
    page_title="Admin Panel - Satta King",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def init_database():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                game_time VARCHAR(50),
                yesterday_result VARCHAR(50),
                today_result VARCHAR(50),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS posts (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT,
                is_published BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS daily_updates (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                content TEXT,
                update_date DATE DEFAULT CURRENT_DATE,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS pages (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                slug VARCHAR(255),
                content TEXT,
                is_published BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS ads (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                ad_code TEXT,
                position VARCHAR(100),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS redirects (
                id SERIAL PRIMARY KEY,
                from_url VARCHAR(500) NOT NULL,
                to_url VARCHAR(500) NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS scrape_settings (
                id SERIAL PRIMARY KEY,
                scrape_url VARCHAR(500),
                auto_scrape BOOLEAN DEFAULT false,
                interval_minutes INTEGER DEFAULT 5,
                last_scrape TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")

init_database()

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    ]
    return random.choice(user_agents)

def scrape_satta_games(url=None):
    if not url:
        url = "https://satta-king-fast.com/"
    
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        time.sleep(random.uniform(1, 3))
        
        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        games_data = []
        
        game_rows = soup.find_all('tr', class_='game-result')
        
        for row in game_rows:
            try:
                game_name_elem = row.find('h3', class_='game-name')
                game_time_elem = row.find('h3', class_='game-time')
                yesterday_elem = row.find('td', class_='yesterday-number')
                today_elem = row.find('td', class_='today-number')
                
                if game_name_elem:
                    game_name = game_name_elem.get_text(strip=True)
                    game_time = game_time_elem.get_text(strip=True) if game_time_elem else ''
                    
                    yesterday_result = '--'
                    if yesterday_elem:
                        result_h3 = yesterday_elem.find('h3')
                        if result_h3:
                            yesterday_result = result_h3.get_text(strip=True)
                            if yesterday_result in ['XX', '--', '']:
                                yesterday_result = '--'
                    
                    today_result = '--'
                    if today_elem:
                        result_h3 = today_elem.find('h3')
                        if result_h3:
                            today_result = result_h3.get_text(strip=True)
                            if today_result in ['XX', '--', '']:
                                today_result = '--'
                    
                    games_data.append({
                        'name': game_name,
                        'game_time': game_time,
                        'yesterday_result': yesterday_result,
                        'today_result': today_result
                    })
            except Exception:
                continue
        
        return games_data, None
    except requests.exceptions.RequestException as e:
        return [], f"Request failed: {str(e)}"
    except Exception as e:
        return [], str(e)

def save_scraped_games(games_data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        saved_count = 0
        updated_count = 0
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        for index, game in enumerate(games_data):
            if 'SHOW YOUR GAME HERE' in game['name'].upper():
                continue
                
            cur.execute("SELECT id FROM games WHERE name = %s", (game['name'],))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE games 
                    SET game_time = %s, yesterday_result = %s, today_result = %s, display_order = %s, updated_at = %s
                    WHERE name = %s
                """, (game['game_time'], game['yesterday_result'], game['today_result'], index, datetime.now(), game['name']))
                updated_count += 1
            else:
                cur.execute("""
                    INSERT INTO games (name, game_time, yesterday_result, today_result, is_active, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (game['name'], game['game_time'], game['yesterday_result'], game['today_result'], True, index))
                saved_count += 1
            
            if game['today_result'] and game['today_result'] != '--' and game['today_result'] != 'XX':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], today, game['today_result'], game['today_result']))
            
            if game['yesterday_result'] and game['yesterday_result'] != '--' and game['yesterday_result'] != 'XX':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], yesterday, game['yesterday_result'], game['yesterday_result']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return saved_count, updated_count, None
    except Exception as e:
        return 0, 0, str(e)

def clear_all_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM games")
        conn.commit()
        cur.close()
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def get_scrape_settings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT scrape_url, auto_scrape, interval_minutes, last_scrape FROM scrape_settings ORDER BY id DESC LIMIT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return {
                'scrape_url': result[0] or 'https://satta-king-fast.com/',
                'auto_scrape': result[1] or False,
                'interval_minutes': result[2] or 5,
                'last_scrape': result[3]
            }
        return {
            'scrape_url': 'https://satta-king-fast.com/',
            'auto_scrape': False,
            'interval_minutes': 5,
            'last_scrape': None
        }
    except:
        return {
            'scrape_url': 'https://satta-king-fast.com/',
            'auto_scrape': False,
            'interval_minutes': 5,
            'last_scrape': None
        }

def save_scrape_settings(url, auto_scrape, interval):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM scrape_settings")
        cur.execute("""
            INSERT INTO scrape_settings (scrape_url, auto_scrape, interval_minutes, last_scrape)
            VALUES (%s, %s, %s, %s)
        """, (url, auto_scrape, interval, datetime.now()))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False

if 'admin_page' not in st.session_state:
    st.session_state.admin_page = 'dashboard'
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

current_time = datetime.now().strftime("%H:%M:%S")
current_date = datetime.now().strftime("%d %b %Y")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebarNav"] {display: none;}
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
    }
    
    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 260px !important;
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%) !important;
        box-shadow: 4px 0 25px rgba(0, 0, 0, 0.5) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
        padding: 0 !important;
    }
    
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    
    [data-testid="stSidebar"][aria-expanded="false"] {
        min-width: 260px !important;
        max-width: 260px !important;
        margin-left: 0 !important;
        transform: none !important;
    }
    
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    .main .block-container {
        padding: 20px 30px !important;
        max-width: 100% !important;
    }
    
    .sidebar-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px 20px;
        text-align: center;
        margin: 15px;
        border-radius: 15px;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .sidebar-logo {
        color: #fff;
        font-size: 22px;
        font-weight: 700;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    .sidebar-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 12px;
        margin-top: 5px;
    }
    
    .sidebar-time {
        background: rgba(255,255,255,0.15);
        color: #fff;
        padding: 8px 15px;
        border-radius: 20px;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        display: inline-block;
        margin-top: 12px;
        backdrop-filter: blur(10px);
    }
    
    .content-header {
        background: linear-gradient(135deg, #1e1e30 0%, #252540 100%);
        padding: 20px 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .content-title {
        font-size: 26px;
        font-weight: 700;
        color: #fff;
        margin: 0;
    }
    
    .admin-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #252540 0%, #2a2a50 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    
    .stat-number {
        font-size: 32px;
        font-weight: 700;
        color: #667eea;
    }
    
    .stat-label {
        color: #a0a0b0;
        font-size: 13px;
        margin-top: 5px;
    }
    
    h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
        color: #e0e0e0 !important;
    }
    
    .stTextInput > div > div > input {
        background: #1a1a2e !important;
        color: #fff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
        padding: 12px 15px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 15px rgba(102, 126, 234, 0.2) !important;
    }
    
    .stTextArea > div > div > textarea {
        background: #1a1a2e !important;
        color: #fff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    
    .stSelectbox > div > div {
        background: #1a1a2e !important;
        border-radius: 10px !important;
    }
    
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 10px 25px !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5) !important;
    }
    
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #2a2a45 0%, #353560 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #fff !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        gap: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        color: #a0a0b0 !important;
        border-radius: 10px 10px 0 0;
        background: transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: #fff !important;
    }
    
    [data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    
    hr {
        border-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    .stAlert {
        background: rgba(102, 126, 234, 0.1) !important;
        border: 1px solid rgba(102, 126, 234, 0.3) !important;
        border-radius: 10px !important;
    }
    
    .scrape-info {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d4a6f 100%);
        border-radius: 12px;
        padding: 15px 20px;
        border: 1px solid rgba(102, 126, 234, 0.3);
        margin-bottom: 15px;
    }
    
    .game-table-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 12px;
        border-radius: 8px 8px 0 0;
        color: #fff;
        font-weight: 600;
    }
    
    .game-row {
        background: rgba(255, 255, 255, 0.03);
        padding: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 240px !important;
            max-width: 240px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

menu_items = [
    ("📊", "Dashboard", "dashboard"),
    ("🎮", "Game", "game"),
    ("📝", "Post", "post"),
    ("📅", "Daily Update", "daily_update"),
    ("📄", "Pages", "pages"),
    ("📢", "Ads", "ads"),
    ("🗺️", "Sitemap", "sitemap"),
    ("🔗", "URL", "url"),
    ("↩️", "Redirects", "redirects"),
]

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="sidebar-logo">Satta King</div>
        <div class="sidebar-subtitle">Admin Panel</div>
        <div class="sidebar-time">{current_time}</div>
    </div>
    """, unsafe_allow_html=True)
    
    for icon, label, page_key in menu_items:
        if st.button(f"{icon}  {label}", key=f"nav_{page_key}", use_container_width=True, 
                    type="primary" if st.session_state.admin_page == page_key else "secondary"):
            st.session_state.admin_page = page_key
            st.session_state.edit_id = None
            st.rerun()
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    if st.button("🚪  Logout", key="nav_logout", use_container_width=True, type="secondary"):
        st.switch_page("app.py")

page_titles = {
    "dashboard": "Dashboard",
    "game": "Game Management",
    "post": "Post Management",
    "daily_update": "Daily Updates",
    "pages": "Pages Management",
    "ads": "Ads Management",
    "sitemap": "Sitemap",
    "url": "URL Management",
    "redirects": "Redirects"
}

st.markdown(f"""
<div class="content-header">
    <span class="content-title">{page_titles.get(st.session_state.admin_page, 'Dashboard')}</span>
    <span class="admin-badge">Administrator</span>
</div>
""", unsafe_allow_html=True)

if st.session_state.admin_page == 'dashboard':
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM games")
    result = cur.fetchone()
    total_games = result[0] if result else 0
    cur.execute("SELECT COUNT(*) FROM posts")
    result = cur.fetchone()
    total_posts = result[0] if result else 0
    cur.execute("SELECT COUNT(*) FROM games WHERE is_active = true")
    result = cur.fetchone()
    active_games = result[0] if result else 0
    cur.close()
    conn.close()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_games}</div>
            <div class="stat-label">Total Games</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{active_games}</div>
            <div class="stat-label">Active Games</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_posts}</div>
            <div class="stat-label">Total Posts</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{current_date}</div>
            <div class="stat-label">Today</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)
    
    st.markdown("### Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Scrape Games", use_container_width=True, type="primary"):
            with st.spinner("Scraping..."):
                games_data, error = scrape_satta_games()
                if error:
                    st.error(f"Failed: {error}")
                elif games_data:
                    saved, updated, _ = save_scraped_games(games_data)
                    st.success(f"Done! New: {saved}, Updated: {updated}")
    with col2:
        if st.button("➕ Add Game", use_container_width=True, type="secondary"):
            st.session_state.admin_page = 'game'
            st.rerun()
    with col3:
        if st.button("📝 Add Post", use_container_width=True, type="secondary"):
            st.session_state.admin_page = 'post'
            st.rerun()

elif st.session_state.admin_page == 'game':
    settings = get_scrape_settings()
    
    st.markdown("### 🔄 Scrape Settings")
    
    st.markdown("""
    <div class="scrape-info">
        <strong>Cloudflare Bypass Enabled</strong><br>
        <small>Using rotating user agents and browser headers to bypass protection</small>
    </div>
    """, unsafe_allow_html=True)
    
    scrape_url = st.text_input("Scrape URL", value=settings['scrape_url'], 
                               placeholder="https://satta-king-fast.com/")
    
    st.markdown("### ⏰ Auto Scrape Schedule")
    
    col1, col2 = st.columns(2)
    with col1:
        auto_scrape = st.checkbox("Enable Auto Scrape", value=settings['auto_scrape'])
    with col2:
        interval = st.selectbox("Interval (minutes)", 
                               options=[1, 2, 5, 10, 15, 30, 60],
                               index=[1, 2, 5, 10, 15, 30, 60].index(settings['interval_minutes']) 
                                     if settings['interval_minutes'] in [1, 2, 5, 10, 15, 30, 60] else 2)
    
    if settings['last_scrape']:
        st.info(f"Last scrape: {settings['last_scrape'].strftime('%d-%m-%Y %H:%M:%S')}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Settings", type="primary", use_container_width=True):
            if save_scrape_settings(scrape_url, auto_scrape, interval):
                st.success("Settings saved!")
            else:
                st.error("Failed to save settings")
    
    with col2:
        if st.button("🔄 Scrape Now", type="secondary", use_container_width=True):
            with st.spinner("Scraping with Cloudflare bypass..."):
                games_data, error = scrape_satta_games(scrape_url)
                if error:
                    st.error(f"Error: {error}")
                elif games_data:
                    saved, updated, save_error = save_scraped_games(games_data)
                    if save_error:
                        st.error(f"Save error: {save_error}")
                    else:
                        st.success(f"✅ Found {len(games_data)} games | New: {saved} | Updated: {updated}")
                        save_scrape_settings(scrape_url, auto_scrape, interval)
                else:
                    st.warning("No games found on the page")
    
    st.markdown("---")
    st.markdown("### 🗑️ Clear All Data")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.warning("This will delete ALL games from the database!")
    with col2:
        if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
            success, error = clear_all_games()
            if success:
                st.success("All games cleared!")
                st.rerun()
            else:
                st.error(f"Error: {error}")
    
    if auto_scrape:
        st.markdown("---")
        st.info(f"⏰ Auto scrape is active! Games will be scraped every {interval} minutes.")
        
        if st.button("▶️ Start Auto Scrape Session", type="primary", use_container_width=True):
            st.info("Auto scraping started. Keep this page open for continuous scraping.")
            
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            for i in range(3):
                with st.spinner(f"Auto scraping... (Run {i+1})"):
                    games_data, error = scrape_satta_games(scrape_url)
                    if games_data:
                        saved, updated, _ = save_scraped_games(games_data)
                        status_placeholder.success(f"Run {i+1}: Found {len(games_data)} | New: {saved} | Updated: {updated}")
                    else:
                        status_placeholder.warning(f"Run {i+1}: No data - {error if error else 'Unknown error'}")
                    
                    if i < 2:
                        for sec in range(interval * 60, 0, -1):
                            progress_placeholder.info(f"Next scrape in {sec} seconds...")
                            time.sleep(1)
            
            st.success("Auto scrape session completed (3 runs). Refresh to run again.")

elif st.session_state.admin_page == 'post':
    tab1, tab2 = st.tabs(["📋 All Posts", "➕ Add Post"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, is_published, created_at FROM posts ORDER BY id DESC")
        posts = cur.fetchall()
        cur.close()
        conn.close()
        
        if posts:
            for post in posts:
                col1, col2, col3, col4 = st.columns([4, 2, 1, 2])
                with col1:
                    st.write(f"**{post[1]}**")
                with col2:
                    st.write(post[3].strftime('%d-%m-%Y') if post[3] else '-')
                with col3:
                    st.write("✅" if post[2] else "📝")
                with col4:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️", key=f"ep_{post[0]}", type="secondary"):
                            st.session_state.edit_id = post[0]
                            st.rerun()
                    with c2:
                        if st.button("🗑️", key=f"dp_{post[0]}", type="secondary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM posts WHERE id = %s", (post[0],))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                st.markdown("---")
        else:
            st.info("No posts found.")
        
        if st.session_state.edit_id:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM posts WHERE id = %s", (st.session_state.edit_id,))
            p = cur.fetchone()
            cur.close()
            conn.close()
            if p:
                st.markdown("### ✏️ Edit Post")
                with st.form("edit_post"):
                    title = st.text_input("Title", value=p[1])
                    content = st.text_area("Content", value=p[2] or "", height=200)
                    published = st.checkbox("Published", value=p[3])
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("💾 Save", type="primary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE posts SET title=%s, content=%s, is_published=%s, updated_at=%s WHERE id=%s",
                                       (title, content, published, datetime.now(), st.session_state.edit_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.edit_id = None
                            st.rerun()
                    with c2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state.edit_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_post"):
            title = st.text_input("Title *")
            content = st.text_area("Content", height=200)
            published = st.checkbox("Publish", value=False)
            if st.form_submit_button("➕ Add Post", type="primary"):
                if title:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO posts (title, content, is_published) VALUES (%s, %s, %s)",
                               (title, content, published))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Post added!")
                    st.rerun()

elif st.session_state.admin_page == 'daily_update':
    tab1, tab2 = st.tabs(["📋 All Updates", "➕ Add Update"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, update_date, is_active FROM daily_updates ORDER BY id DESC")
        updates = cur.fetchall()
        cur.close()
        conn.close()
        
        if updates:
            for u in updates:
                col1, col2, col3, col4 = st.columns([4, 2, 1, 2])
                with col1:
                    st.write(f"**{u[1]}**")
                with col2:
                    st.write(str(u[2]) if u[2] else '-')
                with col3:
                    st.write("✅" if u[3] else "❌")
                with col4:
                    if st.button("🗑️", key=f"du_{u[0]}", type="secondary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM daily_updates WHERE id = %s", (u[0],))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No updates found.")
    
    with tab2:
        with st.form("add_update"):
            title = st.text_input("Title *")
            content = st.text_area("Content", height=150)
            active = st.checkbox("Active", value=True)
            if st.form_submit_button("➕ Add Update", type="primary"):
                if title:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO daily_updates (title, content, is_active) VALUES (%s, %s, %s)",
                               (title, content, active))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Update added!")
                    st.rerun()

elif st.session_state.admin_page == 'pages':
    tab1, tab2 = st.tabs(["📋 All Pages", "➕ Add Page"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, slug, is_published FROM pages ORDER BY id DESC")
        pages = cur.fetchall()
        cur.close()
        conn.close()
        
        if pages:
            for pg in pages:
                col1, col2, col3, col4 = st.columns([3, 3, 1, 2])
                with col1:
                    st.write(f"**{pg[1]}**")
                with col2:
                    st.write(f"/{pg[2]}" if pg[2] else '-')
                with col3:
                    st.write("✅" if pg[3] else "📝")
                with col4:
                    if st.button("🗑️", key=f"pg_{pg[0]}", type="secondary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM pages WHERE id = %s", (pg[0],))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No pages found.")
    
    with tab2:
        with st.form("add_page"):
            title = st.text_input("Title *")
            slug = st.text_input("Slug (URL)")
            content = st.text_area("Content", height=200)
            published = st.checkbox("Publish", value=False)
            if st.form_submit_button("➕ Add Page", type="primary"):
                if title:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO pages (title, slug, content, is_published) VALUES (%s, %s, %s, %s)",
                               (title, slug, content, published))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Page added!")
                    st.rerun()

elif st.session_state.admin_page == 'ads':
    tab1, tab2 = st.tabs(["📋 All Ads", "➕ Add Ad"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, position, is_active FROM ads ORDER BY id DESC")
        ads = cur.fetchall()
        cur.close()
        conn.close()
        
        if ads:
            for ad in ads:
                col1, col2, col3, col4 = st.columns([3, 3, 1, 2])
                with col1:
                    st.write(f"**{ad[1]}**")
                with col2:
                    st.write(ad[2] or '-')
                with col3:
                    st.write("✅" if ad[3] else "❌")
                with col4:
                    if st.button("🗑️", key=f"ad_{ad[0]}", type="secondary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM ads WHERE id = %s", (ad[0],))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No ads found.")
    
    with tab2:
        with st.form("add_ad"):
            name = st.text_input("Ad Name *")
            position = st.selectbox("Position", ["Header", "Sidebar", "Content", "Footer"])
            ad_code = st.text_area("Ad Code", height=150)
            active = st.checkbox("Active", value=True)
            if st.form_submit_button("➕ Add Ad", type="primary"):
                if name:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO ads (name, position, ad_code, is_active) VALUES (%s, %s, %s, %s)",
                               (name, position, ad_code, active))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Ad added!")
                    st.rerun()

elif st.session_state.admin_page == 'sitemap':
    st.markdown("### 🗺️ Sitemap Generator")
    st.info("Generate XML sitemap for your website")
    
    if st.button("Generate Sitemap", type="primary"):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT slug FROM pages WHERE is_published = true")
        pages = cur.fetchall()
        cur.close()
        conn.close()
        
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        sitemap += '  <url><loc>https://yoursite.com/</loc></url>\n'
        for pg in pages:
            if pg[0]:
                sitemap += f'  <url><loc>https://yoursite.com/{pg[0]}</loc></url>\n'
        sitemap += '</urlset>'
        
        st.code(sitemap, language="xml")
        st.success("Sitemap generated!")

elif st.session_state.admin_page == 'url':
    st.markdown("### 🔗 URL Settings")
    st.info("Manage your website URLs and permalinks")
    
    with st.form("url_settings"):
        base_url = st.text_input("Base URL", value="https://yoursite.com")
        permalink = st.selectbox("Permalink Structure", ["/%postname%/", "/%year%/%monthnum%/%postname%/", "/%category%/%postname%/"])
        if st.form_submit_button("💾 Save Settings", type="primary"):
            st.success("URL settings saved!")

elif st.session_state.admin_page == 'redirects':
    tab1, tab2 = st.tabs(["📋 All Redirects", "➕ Add Redirect"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, from_url, to_url, is_active FROM redirects ORDER BY id DESC")
        redirects = cur.fetchall()
        cur.close()
        conn.close()
        
        if redirects:
            for r in redirects:
                col1, col2, col3, col4 = st.columns([3, 3, 1, 2])
                with col1:
                    st.write(f"{r[1]}")
                with col2:
                    st.write(f"→ {r[2]}")
                with col3:
                    st.write("✅" if r[3] else "❌")
                with col4:
                    if st.button("🗑️", key=f"rd_{r[0]}", type="secondary"):
                        conn = get_db_connection()
                        cur = conn.cursor()
                        cur.execute("DELETE FROM redirects WHERE id = %s", (r[0],))
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.rerun()
                st.markdown("---")
        else:
            st.info("No redirects found.")
    
    with tab2:
        with st.form("add_redirect"):
            from_url = st.text_input("From URL *")
            to_url = st.text_input("To URL *")
            active = st.checkbox("Active", value=True)
            if st.form_submit_button("➕ Add Redirect", type="primary"):
                if from_url and to_url:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO redirects (from_url, to_url, is_active) VALUES (%s, %s, %s)",
                               (from_url, to_url, active))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Redirect added!")
                    st.rerun()
