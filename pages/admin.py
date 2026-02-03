import streamlit as st
import psycopg2
import os
from datetime import datetime

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
    
    .admin-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .admin-title {
        color: white;
        font-size: 28px;
        font-weight: bold;
        margin: 0;
    }
    
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    
    .success-msg {
        background: #d4edda;
        color: #155724;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    
    .error-msg {
        background: #f8d7da;
        color: #721c24;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="admin-header">
    <h1 class="admin-title">⚙️ Admin Panel</h1>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 📋 Menu")
    
    if st.button("🎮 Game", use_container_width=True, type="primary" if st.session_state.current_page == 'games' else "secondary"):
        st.session_state.current_page = 'games'
        st.session_state.edit_game_id = None
        st.rerun()
    
    if st.button("📝 Post", use_container_width=True, type="primary" if st.session_state.current_page == 'posts' else "secondary"):
        st.session_state.current_page = 'posts'
        st.session_state.edit_post_id = None
        st.rerun()

if st.session_state.current_page == 'games':
    st.subheader("🎮 Game Management")
    
    tab1, tab2 = st.tabs(["📋 All Games", "➕ Add New Game"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, result, result_time, is_active FROM games ORDER BY id DESC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        
        if games:
            for game in games:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 2])
                    with col1:
                        st.write(f"**{game[1]}**")
                    with col2:
                        st.write(f"Result: {game[2] or '-'}")
                    with col3:
                        st.write(f"Time: {game[3] or '-'}")
                    with col4:
                        status = "✅" if game[4] else "❌"
                        st.write(status)
                    with col5:
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️", key=f"edit_game_{game[0]}"):
                                st.session_state.edit_game_id = game[0]
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_game_{game[0]}"):
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("DELETE FROM games WHERE id = %s", (game[0],))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.rerun()
                    st.divider()
        else:
            st.info("No games found. Add your first game!")
        
        if st.session_state.edit_game_id:
            st.subheader("✏️ Edit Game")
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
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
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
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.edit_game_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_game_form"):
            game_name = st.text_input("Game Name *")
            game_result = st.text_input("Result (optional)")
            game_time = st.text_input("Result Time (e.g., 11:00 PM)")
            game_active = st.checkbox("Active", value=True)
            
            if st.form_submit_button("➕ Add Game", use_container_width=True):
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
                    st.success(f"Game '{game_name}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter game name!")

elif st.session_state.current_page == 'posts':
    st.subheader("📝 Post Management")
    
    tab1, tab2 = st.tabs(["📋 All Posts", "➕ Add New Post"])
    
    with tab1:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, title, content, is_published, created_at FROM posts ORDER BY id DESC")
        posts = cur.fetchall()
        cur.close()
        conn.close()
        
        if posts:
            for post in posts:
                with st.container():
                    col1, col2, col3, col4 = st.columns([4, 2, 1, 2])
                    with col1:
                        st.write(f"**{post[1]}**")
                    with col2:
                        st.write(f"{post[4].strftime('%d-%m-%Y') if post[4] else '-'}")
                    with col3:
                        status = "✅" if post[3] else "📝"
                        st.write(status)
                    with col4:
                        col_edit, col_del = st.columns(2)
                        with col_edit:
                            if st.button("✏️", key=f"edit_post_{post[0]}"):
                                st.session_state.edit_post_id = post[0]
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_post_{post[0]}"):
                                conn = get_db_connection()
                                cur = conn.cursor()
                                cur.execute("DELETE FROM posts WHERE id = %s", (post[0],))
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.rerun()
                    st.divider()
        else:
            st.info("No posts found. Add your first post!")
        
        if st.session_state.edit_post_id:
            st.subheader("✏️ Edit Post")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, title, content, is_published FROM posts WHERE id = %s", (st.session_state.edit_post_id,))
            post_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if post_data:
                with st.form("edit_post_form"):
                    edit_title = st.text_input("Post Title", value=post_data[1])
                    edit_content = st.text_area("Content", value=post_data[2] or "", height=200)
                    edit_published = st.checkbox("Published", value=post_data[3])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
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
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.session_state.edit_post_id = None
                            st.rerun()
    
    with tab2:
        with st.form("add_post_form"):
            post_title = st.text_input("Post Title *")
            post_content = st.text_area("Content", height=200)
            post_published = st.checkbox("Publish immediately", value=False)
            
            if st.form_submit_button("➕ Add Post", use_container_width=True):
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
                    st.success(f"Post '{post_title}' added successfully!")
                    st.rerun()
                else:
                    st.error("Please enter post title!")
