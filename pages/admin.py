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
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Database connection error: {e}")

init_database()

def scrape_satta_games():
    try:
        url = "https://satta-king-fast.com/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
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
                    
                    games_data.append({
                        'name': game_name,
                        'result': today_result,
                        'result_time': game_time
                    })
            except Exception as e:
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
                cur.execute("""
                    UPDATE games 
                    SET result = %s, result_time = %s, updated_at = %s
                    WHERE name = %s
                """, (game['result'], game['result_time'], datetime.now(), game['name']))
                updated_count += 1
            else:
                cur.execute("""
                    INSERT INTO games (name, result, result_time, is_active)
                    VALUES (%s, %s, %s, %s)
                """, (game['name'], game['result'], game['result_time'], True))
                saved_count += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        return saved_count, updated_count, None
    except Exception as e:
        return 0, 0, str(e)

def init_session_state():
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'games'
    if 'edit_game_id' not in st.session_state:
        st.session_state.edit_game_id = None
    if 'edit_post_id' not in st.session_state:
        st.session_state.edit_post_id = None

init_session_state()

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    [data-testid="stSidebarNav"] {display: none;}
    
    [data-testid="stSidebar"] {
        min-width: 240px !important;
        max-width: 240px !important;
        width: 240px !important;
        background: #1e272e !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: #1e272e !important;
        padding-top: 0 !important;
    }
    
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
        background: #f5f5f5;
    }
    
    .stApp {
        background: #f5f5f5;
    }
    
    .sidebar-header {
        background: #1e272e;
        padding: 20px 15px;
        text-align: center;
        border-bottom: 1px solid #2d3436;
    }
    
    .sidebar-logo {
        color: #00d2d3;
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    .sidebar-time {
        background: #2d3436;
        color: #00d2d3;
        padding: 8px 15px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 14px;
        display: inline-block;
    }
    
    .menu-item {
        display: flex;
        align-items: center;
        padding: 12px 20px;
        color: #b2bec3;
        text-decoration: none;
        cursor: pointer;
        transition: all 0.3s;
        border-left: 3px solid transparent;
        margin: 2px 0;
    }
    
    .menu-item:hover {
        background: #2d3436;
        color: #fff;
    }
    
    .menu-item.active {
        background: #00b894;
        color: #fff;
        border-left: 3px solid #00d2d3;
    }
    
    .menu-icon {
        margin-right: 12px;
        font-size: 18px;
    }
    
    .content-header {
        background: #fff;
        padding: 15px 25px;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .content-title {
        font-size: 22px;
        font-weight: 600;
        color: #2d3436;
        margin: 0;
    }
    
    .admin-badge {
        color: #636e72;
        font-size: 14px;
    }
    
    .content-body {
        padding: 25px;
    }
    
    .content-card {
        background: #fff;
        border-radius: 8px;
        padding: 25px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    .stButton > button {
        border-radius: 5px;
        font-weight: 500;
    }
    
    .stButton > button[kind="primary"] {
        background: #00b894 !important;
        border-color: #00b894 !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #00a884 !important;
    }
    
    div[data-testid="stVerticalBlock"] > div {
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background: transparent;
        border-bottom: 2px solid #e0e0e0;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        font-weight: 500;
        color: #636e72;
        border-radius: 0;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
    }
    
    .stTabs [aria-selected="true"] {
        color: #00b894 !important;
        border-bottom: 2px solid #00b894 !important;
        background: transparent !important;
    }
    
    .game-row {
        background: #f8f9fa;
        padding: 12px 15px;
        border-radius: 6px;
        margin-bottom: 8px;
        border-left: 3px solid #00b894;
    }
    
    @media (max-width: 768px) {
        [data-testid="stSidebar"] {
            min-width: 200px !important;
            max-width: 200px !important;
            width: 200px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

current_time = datetime.now().strftime("%H:%M:%S")

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-header">
        <div class="sidebar-logo">Satta King</div>
        <div class="sidebar-logo" style="font-size: 14px; color: #b2bec3;">Admin</div>
        <div style="margin-top: 10px;">
            <span class="sidebar-time">Server: {current_time}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    
    game_active = "primary" if st.session_state.current_page == 'games' else "secondary"
    post_active = "primary" if st.session_state.current_page == 'posts' else "secondary"
    
    if st.button("🎮  Game", use_container_width=True, type=game_active):
        st.session_state.current_page = 'games'
        st.session_state.edit_game_id = None
        st.rerun()
    
    if st.button("📝  Post", use_container_width=True, type=post_active):
        st.session_state.current_page = 'posts'
        st.session_state.edit_post_id = None
        st.rerun()
    
    st.markdown("<div style='height: 200px'></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🏠  Back to Site", use_container_width=True, type="secondary"):
        st.switch_page("app.py")

col_header = st.columns([6, 1])
with col_header[0]:
    if st.session_state.current_page == 'games':
        st.markdown('<p class="content-title">Game Management</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="content-title">Post Management</p>', unsafe_allow_html=True)
with col_header[1]:
    st.markdown('<p class="admin-badge">Administrator</p>', unsafe_allow_html=True)

st.markdown("---")

if st.session_state.current_page == 'games':
    
    tab1, tab2, tab3 = st.tabs(["All Games", "Add Game", "Scrape"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, result, result_time, is_active FROM games ORDER BY id DESC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        
        if games:
            st.write(f"**Total Games: {len(games)}**")
            st.markdown("")
            
            for game in games:
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 2])
                with col1:
                    st.write(f"**{game[1]}**")
                with col2:
                    st.write(f"{game[2] or '--'}")
                with col3:
                    st.write(f"{game[3] or '--'}")
                with col4:
                    st.write("✅" if game[4] else "❌")
                with col5:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Edit", key=f"edit_{game[0]}", type="secondary"):
                            st.session_state.edit_game_id = game[0]
                            st.rerun()
                    with c2:
                        if st.button("Del", key=f"del_{game[0]}", type="secondary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM games WHERE id = %s", (game[0],))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                st.markdown("---")
        else:
            st.info("No games found. Add your first game!")
        
        if st.session_state.edit_game_id:
            st.markdown("### Edit Game")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, name, result, result_time, is_active FROM games WHERE id = %s", (st.session_state.edit_game_id,))
            game_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if game_data:
                with st.form("edit_game_form"):
                    edit_name = st.text_input("Game Name", value=game_data[1])
                    edit_result = st.text_input("Result", value=game_data[2] or "")
                    edit_time = st.text_input("Result Time", value=game_data[3] or "")
                    edit_active = st.checkbox("Active", value=game_data[4])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save", use_container_width=True, type="primary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE games 
                                SET name = %s, result = %s, result_time = %s, is_active = %s, updated_at = %s
                                WHERE id = %s
                            """, (edit_name, edit_result, edit_time, edit_active, datetime.now(), st.session_state.edit_game_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.edit_game_id = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.edit_game_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_game_form"):
            game_name = st.text_input("Game Name *")
            game_result = st.text_input("Result (optional)")
            game_time = st.text_input("Result Time (e.g., 11:00 PM)")
            game_active = st.checkbox("Active", value=True)
            
            if st.form_submit_button("Add Game", use_container_width=True, type="primary"):
                if game_name:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO games (name, result, result_time, is_active)
                        VALUES (%s, %s, %s, %s)
                    """, (game_name, game_result, game_time, game_active))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"Game '{game_name}' added!")
                    st.rerun()
                else:
                    st.error("Please enter game name!")
    
    with tab3:
        st.info("Scrape realtime game results from satta-king-fast.com")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Scrape Now", use_container_width=True, type="primary"):
                with st.spinner("Scraping..."):
                    games_data, error = scrape_satta_games()
                    
                    if error:
                        st.error(f"Failed: {error}")
                    elif games_data:
                        st.success(f"Found {len(games_data)} games!")
                        
                        saved, updated, save_error = save_scraped_games(games_data)
                        
                        if save_error:
                            st.error(f"Error: {save_error}")
                        else:
                            st.success(f"New: {saved} | Updated: {updated}")
                    else:
                        st.warning("No games found.")
        
        with col2:
            if st.button("Delete All", use_container_width=True, type="secondary"):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM games")
                conn.commit()
                cur.close()
                conn.close()
                st.success("All games deleted!")
                st.rerun()

elif st.session_state.current_page == 'posts':
    
    tab1, tab2 = st.tabs(["All Posts", "Add Post"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, is_published, created_at FROM posts ORDER BY id DESC")
        posts = cur.fetchall()
        cur.close()
        conn.close()
        
        if posts:
            st.write(f"**Total Posts: {len(posts)}**")
            st.markdown("")
            
            for post in posts:
                col1, col2, col3, col4 = st.columns([4, 2, 1, 2])
                with col1:
                    st.write(f"**{post[1]}**")
                with col2:
                    st.write(f"{post[4].strftime('%d-%m-%Y') if post[4] else '-'}")
                with col3:
                    st.write("✅" if post[3] else "📝")
                with col4:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Edit", key=f"edit_post_{post[0]}", type="secondary"):
                            st.session_state.edit_post_id = post[0]
                            st.rerun()
                    with c2:
                        if st.button("Del", key=f"del_post_{post[0]}", type="secondary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("DELETE FROM posts WHERE id = %s", (post[0],))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.rerun()
                st.markdown("---")
        else:
            st.info("No posts found. Add your first post!")
        
        if st.session_state.edit_post_id:
            st.markdown("### Edit Post")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, content, is_published FROM posts WHERE id = %s", (st.session_state.edit_post_id,))
            post_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if post_data:
                with st.form("edit_post_form"):
                    edit_title = st.text_input("Title", value=post_data[1])
                    edit_content = st.text_area("Content", value=post_data[2] or "", height=200)
                    edit_published = st.checkbox("Published", value=post_data[3])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save", use_container_width=True, type="primary"):
                            conn = get_db_connection()
                            cur = conn.cursor()
                            cur.execute("""
                                UPDATE posts 
                                SET title = %s, content = %s, is_published = %s, updated_at = %s
                                WHERE id = %s
                            """, (edit_title, edit_content, edit_published, datetime.now(), st.session_state.edit_post_id))
                            conn.commit()
                            cur.close()
                            conn.close()
                            st.session_state.edit_post_id = None
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.edit_post_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_post_form"):
            post_title = st.text_input("Title *")
            post_content = st.text_area("Content", height=200)
            post_published = st.checkbox("Publish immediately", value=False)
            
            if st.form_submit_button("Add Post", use_container_width=True, type="primary"):
                if post_title:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO posts (title, content, is_published)
                        VALUES (%s, %s, %s)
                    """, (post_title, post_content, post_published))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.success(f"Post '{post_title}' added!")
                    st.rerun()
                else:
                    st.error("Please enter title!")
