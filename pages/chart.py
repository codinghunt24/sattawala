import streamlit as st
import psycopg2
import os
from datetime import datetime
import calendar

st.set_page_config(page_title="Record Chart - Satta King", page_icon="📊", layout="wide")

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def get_game_results(game_name, month, year):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT result_date, result 
            FROM game_results 
            WHERE game_name = %s 
            AND EXTRACT(MONTH FROM result_date) = %s 
            AND EXTRACT(YEAR FROM result_date) = %s
            ORDER BY result_date ASC
        """, (game_name, month, year))
        results = cur.fetchall()
        cur.close()
        conn.close()
        return {r[0].day: r[1] for r in results}
    except:
        return {}

def get_all_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name FROM games WHERE is_active = true ORDER BY name ASC")
        games = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return games
    except Exception as e:
        st.error(f"Error loading games: {e}")
        return []

game_name = st.query_params.get("game", "")
games_list = get_all_games()

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    .stApp {
        background: transparent;
    }
    
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    .stMainBlockContainer {
        padding-top: 20px !important;
        padding-left: 5px !important;
        padding-right: 5px !important;
    }
    
    @media (min-width: 768px) {
        .stMainBlockContainer {
            padding-left: 10% !important;
            padding-right: 10% !important;
        }
    }
    
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 8px !important;
    }
    
    [data-testid="stHorizontalBlock"] > div {
        min-width: 0 !important;
        flex: 1 !important;
    }
    
    [data-testid="stHorizontalBlock"] label {
        font-size: 11px !important;
    }
    
    [data-testid="stHorizontalBlock"] .stSelectbox > div > div {
        font-size: 12px !important;
        padding: 5px 8px !important;
    }
    
    .chart-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    .chart-title {
        color: #fff;
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }
    
    .chart-subtitle {
        color: rgba(255,255,255,0.8);
        font-size: 14px;
        margin-top: 5px;
    }
    
    .back-btn {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #fff !important;
        padding: 10px 25px;
        border-radius: 25px;
        text-decoration: none !important;
        font-weight: 600;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .results-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        margin-top: 20px;
    }
    
    .results-table thead {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .results-table th {
        color: #fff;
        padding: 15px 10px;
        font-weight: 600;
        font-size: 14px;
        text-transform: uppercase;
        text-align: center;
    }
    
    .results-table tbody tr {
        background: linear-gradient(135deg, #252540 0%, #2a2a50 100%);
    }
    
    .results-table tbody tr:nth-child(even) {
        background: linear-gradient(135deg, #1e1e35 0%, #252545 100%);
    }
    
    .results-table td {
        padding: 12px 10px;
        text-align: center;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        color: #fff;
    }
    
    .date-cell {
        color: #00d4ff;
        font-weight: 600;
    }
    
    .result-cell {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        color: #fff;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: 700;
        display: inline-block;
        min-width: 40px;
    }
    
    .result-pending {
        background: linear-gradient(135deg, #7f8c8d 0%, #95a5a6 100%);
        color: #fff;
        padding: 8px 15px;
        border-radius: 8px;
        font-weight: 700;
        display: inline-block;
        min-width: 40px;
    }
    
    .no-results {
        text-align: center;
        padding: 40px;
        color: #a0a0b0;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<a href="/" class="back-btn">← Back to Home</a>', unsafe_allow_html=True)

st.markdown(f"""
<div class="chart-header">
    <div class="chart-title">📊 Record Chart</div>
    <div class="chart-subtitle">{game_name if game_name else "Select a game"}</div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    if games_list:
        selected_game = st.selectbox("Select Game", games_list, index=games_list.index(game_name) if game_name in games_list else 0)
    else:
        selected_game = game_name
        st.warning("No games available")

with col2:
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    current_month = datetime.now().month
    selected_month = st.selectbox("Select Month", months, index=current_month - 1)
    month_num = months.index(selected_month) + 1

with col3:
    current_year = datetime.now().year
    years = list(range(current_year, current_year - 5, -1))
    selected_year = st.selectbox("Select Year", years)

if selected_game:
    results = get_game_results(selected_game, month_num, selected_year)
    days_in_month = calendar.monthrange(selected_year, month_num)[1]
    
    table_html = '<table class="results-table"><thead><tr><th>Date</th><th>Result</th></tr></thead><tbody>'
    
    for day in range(1, days_in_month + 1):
        result = results.get(day, '--')
        result_class = "result-pending" if result == '--' else "result-cell"
        date_str = f"{day:02d}-{month_num:02d}-{selected_year}"
        table_html += f'<tr><td class="date-cell">{date_str}</td><td><span class="{result_class}">{result}</span></td></tr>'
    
    table_html += '</tbody></table>'
    
    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.markdown('<div class="no-results">Please select a game to view results</div>', unsafe_allow_html=True)
