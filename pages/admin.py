import streamlit as st
import psycopg2
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

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
                result VARCHAR(50),
                result_time VARCHAR(50),
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
                slug VARCHAR(255) UNIQUE,
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
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")

init_database()

def scrape_satta_games():
    try:
        url = "https://satta-king-fast.com/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        games_data = []
        game_rows = soup.find_all('tr', class_='game-result')
        for row in game_rows:
            try:
                game_name_elem = row.find('h3', class_='game-name')
                game_time_elem = row.find('h3', class_='game-time')
                today_result_elem = row.find('td', class_='today-number')
                if game_name_elem:
                    game_name = game_name_elem.get_text(strip=True)
                    game_time = game_time_elem.get_text(strip=True).replace('at ', '') if game_time_elem else ''
                    today_result = '--'
                    if today_result_elem:
                        result_h3 = today_result_elem.find('h3')
                        if result_h3:
                            today_result = result_h3.get_text(strip=True)
                            if today_result in ['XX', '--', '']:
                                today_result = '--'
                    games_data.append({'name': game_name, 'result': today_result, 'result_time': game_time})
            except:
                continue
        return games_data, None
    except Exception as e:
        return [], str(e)

def save_scraped_games(games_data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        saved_count = 0
        updated_count = 0
        for game in games_data:
            cur.execute("SELECT id FROM games WHERE name = %s", (game['name'],))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE games SET result = %s, result_time = %s, updated_at = %s WHERE name = %s",
                           (game['result'], game['result_time'], datetime.now(), game['name']))
                updated_count += 1
            else:
                cur.execute("INSERT INTO games (name, result, result_time, is_active) VALUES (%s, %s, %s, %s)",
                           (game['name'], game['result'], game['result_time'], True))
                saved_count += 1
        conn.commit()
        cur.close()
        conn.close()
        return saved_count, updated_count, None
    except Exception as e:
        return 0, 0, str(e)

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
    
    .nav-item {
        background: linear-gradient(135deg, #1e1e30 0%, #252540 100%);
        margin: 8px 15px;
        padding: 14px 18px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        transition: all 0.3s ease;
        cursor: pointer;
        display: flex;
        align-items: center;
        color: #a0a0b0;
    }
    
    .nav-item:hover {
        background: linear-gradient(135deg, #2a2a45 0%, #353560 100%);
        border-color: rgba(102, 126, 234, 0.3);
        transform: translateX(5px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.15);
    }
    
    .nav-item.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff;
        border-color: transparent;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .nav-icon {
        font-size: 18px;
        margin-right: 12px;
        width: 24px;
        text-align: center;
    }
    
    .nav-text {
        font-size: 14px;
        font-weight: 500;
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
    
    .content-card {
        background: linear-gradient(135deg, #1e1e30 0%, #252540 100%);
        border-radius: 15px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
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
    
    .logout-btn {
        background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
        margin: 8px 15px;
        padding: 14px 18px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 15px rgba(231, 76, 60, 0.3);
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
        active_class = "active" if st.session_state.admin_page == page_key else ""
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
    tab1, tab2, tab3 = st.tabs(["📋 All Games", "➕ Add Game", "🔄 Scrape"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, result, result_time, is_active FROM games ORDER BY id DESC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        
        if games:
            st.markdown(f"**Total: {len(games)} games**")
            for game in games:
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 2])
                with col1:
                    st.write(f"**{game[1]}**")
                with col2:
                    st.write(game[2] or '--')
                with col3:
                    st.write(game[3] or '--')
                with col4:
                    st.write("✅" if game[4] else "❌")
                with col5:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Edit", key=f"eg_{game[0]}", type="secondary"):
                            st.session_state.edit_id = game[0]
                            st.rerun()
                    with c2:
                        if st.button("Del", key=f"dg_{game[0]}", type="secondary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM games WHERE id = %s", (game[0],))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                st.markdown("---")
        else:
            st.info("No games found.")
        
        if st.session_state.edit_id:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM games WHERE id = %s", (st.session_state.edit_id,))
            g = cur.fetchone()
            cur.close()
            conn.close()
            if g:
                st.markdown("### Edit Game")
                with st.form("edit_game"):
                    name = st.text_input("Name", value=g[1])
                    result = st.text_input("Result", value=g[2] or "")
                    time = st.text_input("Time", value=g[3] or "")
                    active = st.checkbox("Active", value=g[4])
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("Save", type="primary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("UPDATE games SET name=%s, result=%s, result_time=%s, is_active=%s, updated_at=%s WHERE id=%s",
                                       (name, result, time, active, datetime.now(), st.session_state.edit_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.edit_id = None
                            st.rerun()
                    with c2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.edit_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_game"):
            name = st.text_input("Game Name *")
            result = st.text_input("Result")
            time = st.text_input("Result Time")
            active = st.checkbox("Active", value=True)
            if st.form_submit_button("Add Game", type="primary"):
                if name:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("INSERT INTO games (name, result, result_time, is_active) VALUES (%s, %s, %s, %s)",
                               (name, result, time, active))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success("Game added!")
                    st.rerun()
    
    with tab3:
        st.info("Scrape games from satta-king-fast.com")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Scrape Now", type="primary", use_container_width=True):
                with st.spinner("Scraping..."):
                    games_data, error = scrape_satta_games()
                    if error:
                        st.error(error)
                    elif games_data:
                        saved, updated, _ = save_scraped_games(games_data)
                        st.success(f"Found {len(games_data)} | New: {saved} | Updated: {updated}")
        with c2:
            if st.button("🗑️ Delete All", type="secondary", use_container_width=True):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM games")
                conn.commit()
                cur.close()
                conn.close()
                st.success("Deleted!")
                st.rerun()

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
                        if st.button("Edit", key=f"ep_{post[0]}", type="secondary"):
                            st.session_state.edit_id = post[0]
                            st.rerun()
                    with c2:
                        if st.button("Del", key=f"dp_{post[0]}", type="secondary"):
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
                st.markdown("### Edit Post")
                with st.form("edit_post"):
                    title = st.text_input("Title", value=p[1])
                    content = st.text_area("Content", value=p[2] or "", height=200)
                    published = st.checkbox("Published", value=p[3])
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.form_submit_button("Save", type="primary"):
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
                        if st.form_submit_button("Cancel"):
                            st.session_state.edit_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_post"):
            title = st.text_input("Title *")
            content = st.text_area("Content", height=200)
            published = st.checkbox("Publish", value=False)
            if st.form_submit_button("Add Post", type="primary"):
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
                    if st.button("Del", key=f"du_{u[0]}", type="secondary"):
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
            if st.form_submit_button("Add Update", type="primary"):
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
                    if st.button("Del", key=f"pg_{pg[0]}", type="secondary"):
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
            if st.form_submit_button("Add Page", type="primary"):
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
                    if st.button("Del", key=f"ad_{ad[0]}", type="secondary"):
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
            if st.form_submit_button("Add Ad", type="primary"):
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
    st.markdown("### Sitemap Generator")
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
    st.markdown("### URL Settings")
    st.info("Manage your website URLs and permalinks")
    
    with st.form("url_settings"):
        base_url = st.text_input("Base URL", value="https://yoursite.com")
        permalink = st.selectbox("Permalink Structure", ["/%postname%/", "/%year%/%monthnum%/%postname%/", "/%category%/%postname%/"])
        if st.form_submit_button("Save Settings", type="primary"):
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
                    if st.button("Del", key=f"rd_{r[0]}", type="secondary"):
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
            if st.form_submit_button("Add Redirect", type="primary"):
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
