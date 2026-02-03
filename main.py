from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import psycopg2
import os
from datetime import datetime, timedelta
import pytz
import re
import json
import requests
from bs4 import BeautifulSoup
import time
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    return datetime.now(IST)

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'satta-king-secret-key')

scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])

def create_slug(name):
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def find_game_by_slug(slug):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM games WHERE is_active = true")
        games = cur.fetchall()
        cur.close()
        conn.close()
        for game in games:
            if create_slug(game[0]) == slug:
                return game[0]
        return None
    except:
        return None

def get_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name, game_time, yesterday_result, today_result FROM games WHERE is_active = true ORDER BY display_order ASC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        return games
    except Exception as e:
        print(f"Error fetching games: {e}")
        return []

def get_all_games_list():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name FROM games WHERE is_active = true ORDER BY name ASC")
        games = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return games
    except Exception as e:
        print(f"Error fetching games list: {e}")
        return []

def get_game_results(game_name, month, year):
    if not game_name:
        return {}
    try:
        month = int(month)
        year = int(year)
        if month < 1 or month > 12:
            return {}
    except (ValueError, TypeError):
        return {}
    
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
    except Exception as e:
        print(f"Error fetching game results for {game_name}: {e}")
        return {}

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
                display_order INTEGER DEFAULT 0,
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
            
            CREATE TABLE IF NOT EXISTS game_results (
                id SERIAL PRIMARY KEY,
                game_name VARCHAR(255) NOT NULL,
                result_date DATE NOT NULL,
                result VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_name, result_date)
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
        print(f"Database init error: {e}")

init_database()

@app.route('/')
def index():
    games = get_games()
    current_date = get_ist_now().strftime("%d-%m-%Y")
    current_time = get_ist_now().strftime("%I:%M:%S %p")
    games_with_slug = []
    for game in games:
        games_with_slug.append({
            'name': game[0],
            'time': game[1] or '--',
            'yesterday': game[2] or '--',
            'today': game[3] or '--',
            'slug': create_slug(game[0])
        })
    return render_template('index.html', games=games_with_slug, current_date=current_date, last_update_time=current_time)

@app.route('/chart')
def chart():
    import calendar
    
    game_slug = request.args.get('game', '')
    month_param = request.args.get('month', '')
    year_param = request.args.get('year', '')
    
    current_month = get_ist_now().month
    current_year = get_ist_now().year
    
    games_list = get_all_games_list()
    game_name = find_game_by_slug(game_slug) if game_slug else (games_list[0] if games_list else '')
    
    try:
        selected_month = int(month_param) if month_param else current_month
        selected_year = int(year_param) if year_param else current_year
    except:
        selected_month = current_month
        selected_year = current_year
    
    if selected_month < 1 or selected_month > 12:
        selected_month = current_month
    
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    month_name = months[selected_month - 1]
    
    results = {}
    days_in_month = 31
    if game_name:
        results = get_game_results(game_name, selected_month, selected_year)
        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    
    seo_title = f"{game_name} Result Chart {month_name} {selected_year} | Satta King Live" if game_name else "Satta King Record Chart | View All Game Results"
    seo_description = f"Check {game_name} Satta King result chart for {month_name} {selected_year}. View daily results, winning numbers, and complete record chart. Updated live with latest {game_name} results." if game_name else "View complete Satta King record charts for all games."
    seo_keywords = f"{game_name}, {game_name} result, {game_name} chart, {game_name} {month_name} {selected_year}, satta king {game_name}, {game_name} record, {game_name} live result" if game_name else "satta king, satta king chart, satta king result"
    canonical_url = f"https://sattaking.replit.app/chart?game={game_slug}" if game_slug else "https://sattaking.replit.app/chart"
    
    schema_data = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": seo_title,
        "description": seo_description,
        "url": canonical_url,
        "dateModified": get_ist_now().isoformat(),
        "mainEntity": {
            "@type": "Dataset",
            "name": f"{game_name} Results - {month_name} {selected_year}" if game_name else "Satta King Results",
            "description": f"Daily result chart for {game_name} game showing all winning numbers for {month_name} {selected_year}" if game_name else "Complete Satta King results",
            "temporalCoverage": f"{selected_year}-{selected_month:02d}"
        },
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://sattaking.replit.app/"},
                {"@type": "ListItem", "position": 2, "name": "Record Chart", "item": "https://sattaking.replit.app/chart"},
                {"@type": "ListItem", "position": 3, "name": game_name or "Chart", "item": canonical_url}
            ]
        }
    }
    
    years = list(range(current_year, current_year - 5, -1))
    
    games_with_slug = [{'name': g, 'slug': create_slug(g)} for g in games_list]
    
    total_results = len([r for r in results.values() if r != '--'])
    results_list = [int(r) for r in results.values() if r != '--' and r.isdigit()]
    avg_result = round(sum(results_list) / len(results_list)) if results_list else 0
    
    related_games = [g for g in games_with_slug if g['name'] != game_name][:5]
    
    faqs = []
    if game_name:
        faqs = [
            {
                "question": f"What is {game_name} Satta King?",
                "answer": f"{game_name} is one of the most popular Satta King games. Results are declared daily and players can check the winning numbers on our website. We provide live updates and complete monthly charts for {game_name}."
            },
            {
                "question": f"What time does {game_name} result come?",
                "answer": f"{game_name} results are updated daily on our website. Check the homepage for the exact timing of result declaration. We update results in real-time as soon as they are announced."
            },
            {
                "question": f"How to check {game_name} result chart?",
                "answer": f"You can view the complete {game_name} result chart by selecting the game, month, and year from the dropdown menus above. Our chart shows all daily results for the selected period."
            },
            {
                "question": f"Is {game_name} result chart accurate?",
                "answer": f"Yes, our {game_name} result chart is updated with accurate information. We source our data from reliable sources and update results in real-time."
            }
        ]
        
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": faq["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": faq["answer"]
                    }
                } for faq in faqs
            ]
        }
        schema_data["hasPart"] = faq_schema
    
    return render_template('chart.html',
        game_name=game_name,
        game_slug=game_slug,
        games_list=games_with_slug,
        months=months,
        selected_month=selected_month,
        month_name=month_name,
        years=years,
        selected_year=selected_year,
        results=results,
        days_in_month=days_in_month,
        seo_title=seo_title,
        seo_description=seo_description,
        seo_keywords=seo_keywords,
        canonical_url=canonical_url,
        schema_data=json.dumps(schema_data, indent=2),
        total_results=total_results,
        avg_result=avg_result,
        related_games=related_games,
        faqs=faqs
    )

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/_stcore/health')
def stcore_health():
    return jsonify({'status': 'ok'})

@app.route('/_stcore/host-config')
def stcore_host_config():
    return jsonify({})

@app.route('/api/games')
def api_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, game_time, yesterday_result, today_result, is_active, display_order FROM games ORDER BY display_order ASC")
        games = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            'id': g[0],
            'name': g[1],
            'game_time': g[2],
            'yesterday_result': g[3],
            'today_result': g[4],
            'is_active': g[5],
            'display_order': g[6]
        } for g in games])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/games', methods=['POST'])
def api_add_game():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO games (name, game_time, yesterday_result, today_result, is_active, display_order)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (data['name'], data.get('game_time', ''), data.get('yesterday_result', '--'), 
              data.get('today_result', '--'), data.get('is_active', True), data.get('display_order', 0)))
        game_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'id': game_id, 'message': 'Game added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/games/<int:game_id>', methods=['PUT'])
def api_update_game(game_id):
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE games SET name=%s, game_time=%s, yesterday_result=%s, today_result=%s, 
            is_active=%s, display_order=%s, updated_at=%s WHERE id=%s
        """, (data['name'], data.get('game_time', ''), data.get('yesterday_result', '--'),
              data.get('today_result', '--'), data.get('is_active', True), 
              data.get('display_order', 0), get_ist_now(), game_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Game updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
def api_delete_game(game_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM games WHERE id = %s", (game_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Game deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    return random.choice(user_agents)

def scrape_satta_games(url=None):
    if not url:
        url = "https://satta-king-fast.com/"
    
    try:
        session = requests.Session()
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
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
            except:
                continue
        
        return games_data, None
    except Exception as e:
        return [], str(e)

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    try:
        games_data, error = scrape_satta_games()
        if error:
            return jsonify({'error': error}), 500
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        saved = 0
        updated = 0
        today = get_ist_now().date()
        yesterday = today - timedelta(days=1)
        
        for index, game in enumerate(games_data):
            if 'SHOW YOUR GAME HERE' in game['name'].upper():
                continue
            
            cur.execute("SELECT id FROM games WHERE name = %s", (game['name'],))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE games SET game_time=%s, yesterday_result=%s, today_result=%s, 
                    display_order=%s, updated_at=%s WHERE name=%s
                """, (game['game_time'], game['yesterday_result'], game['today_result'], 
                      index, get_ist_now(), game['name']))
                updated += 1
            else:
                cur.execute("""
                    INSERT INTO games (name, game_time, yesterday_result, today_result, is_active, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (game['name'], game['game_time'], game['yesterday_result'], game['today_result'], True, index))
                saved += 1
            
            if game['today_result'] and game['today_result'] != '--':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], today, game['today_result'], game['today_result']))
            
            if game['yesterday_result'] and game['yesterday_result'] != '--':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], yesterday, game['yesterday_result'], game['yesterday_result']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'saved': saved, 'updated': updated, 'total': len(games_data)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-games', methods=['POST'])
def api_clear_games():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM games")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'All games cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_scrape_settings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, scrape_url, auto_scrape, interval_minutes, last_scrape FROM scrape_settings LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                'id': row[0],
                'scrape_url': row[1] or 'https://satta-king-fast.com/',
                'auto_scrape': row[2] or False,
                'interval_minutes': row[3] or 5,
                'last_scrape': row[4].isoformat() if row[4] else None
            }
        return {
            'id': None,
            'scrape_url': 'https://satta-king-fast.com/',
            'auto_scrape': False,
            'interval_minutes': 5,
            'last_scrape': None
        }
    except Exception as e:
        print(f"Error getting scrape settings: {e}")
        return {'auto_scrape': False, 'interval_minutes': 5, 'last_scrape': None}

def update_last_scrape():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE scrape_settings SET last_scrape = %s WHERE id = (SELECT id FROM scrape_settings LIMIT 1)", (get_ist_now(),))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating last scrape: {e}")

def auto_scrape_job():
    print(f"[{get_ist_now()}] Running auto-scrape job...")
    try:
        games_data, error = scrape_satta_games()
        if error:
            print(f"Auto-scrape error: {error}")
            return
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        today = get_ist_now().date()
        yesterday = today - timedelta(days=1)
        
        for index, game in enumerate(games_data):
            if 'SHOW YOUR GAME HERE' in game['name'].upper():
                continue
            
            cur.execute("SELECT id FROM games WHERE name = %s", (game['name'],))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE games SET game_time=%s, yesterday_result=%s, today_result=%s, 
                    display_order=%s, updated_at=%s WHERE name=%s
                """, (game['game_time'], game['yesterday_result'], game['today_result'], 
                      index, get_ist_now(), game['name']))
            else:
                cur.execute("""
                    INSERT INTO games (name, game_time, yesterday_result, today_result, is_active, display_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (game['name'], game['game_time'], game['yesterday_result'], game['today_result'], True, index))
            
            if game['today_result'] and game['today_result'] != '--':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], today, game['today_result'], game['today_result']))
            
            if game['yesterday_result'] and game['yesterday_result'] != '--':
                cur.execute("""
                    INSERT INTO game_results (game_name, result_date, result)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (game_name, result_date) DO UPDATE SET result = %s
                """, (game['name'], yesterday, game['yesterday_result'], game['yesterday_result']))
        
        conn.commit()
        cur.close()
        conn.close()
        update_last_scrape()
        print(f"[{get_ist_now()}] Auto-scrape completed: {len(games_data)} games processed")
    except Exception as e:
        print(f"Auto-scrape job error: {e}")

def setup_auto_scrape():
    settings = get_scrape_settings()
    try:
        if scheduler.get_job('auto_scrape'):
            scheduler.remove_job('auto_scrape')
    except:
        pass
    
    if settings.get('auto_scrape'):
        interval = settings.get('interval_minutes', 5)
        scheduler.add_job(
            auto_scrape_job,
            IntervalTrigger(minutes=interval),
            id='auto_scrape',
            replace_existing=True
        )
        print(f"Auto-scrape scheduled every {interval} minutes")

@app.route('/api/scrape-settings', methods=['GET'])
def api_get_scrape_settings():
    return jsonify(get_scrape_settings())

@app.route('/api/scrape-settings', methods=['POST'])
def api_update_scrape_settings():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM scrape_settings LIMIT 1")
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE scrape_settings SET auto_scrape=%s, interval_minutes=%s WHERE id=%s
            """, (data.get('auto_scrape', False), data.get('interval_minutes', 5), existing[0]))
        else:
            cur.execute("""
                INSERT INTO scrape_settings (scrape_url, auto_scrape, interval_minutes)
                VALUES (%s, %s, %s)
            """, ('https://satta-king-fast.com/', data.get('auto_scrape', False), data.get('interval_minutes', 5)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        setup_auto_scrape()
        
        return jsonify({'message': 'Settings updated', 'auto_scrape': data.get('auto_scrape'), 'interval_minutes': data.get('interval_minutes')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

setup_auto_scrape()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
