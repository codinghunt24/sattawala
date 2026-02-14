from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, session
from functools import wraps
import hashlib
from werkzeug.utils import secure_filename
import psycopg2
import os
from datetime import datetime, timedelta
import pytz
import re
import json
import requests
import cloudscraper
from bs4 import BeautifulSoup
import time
import random
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import base64
from pathlib import Path

env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    return datetime.now(IST)

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'satta-king-secret-key')

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise Exception("DATABASE_URL environment variable is not set. Please configure your database connection.")
    return psycopg2.connect(db_url)

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
            
            CREATE TABLE IF NOT EXISTS site_settings (
                id SERIAL PRIMARY KEY,
                logo_data TEXT,
                favicon_data TEXT,
                site_title VARCHAR(255) DEFAULT 'Satta King',
                ga_tracking_id VARCHAR(50),
                redirect_404_enabled BOOLEAN DEFAULT true,
                redirect_404_url VARCHAR(500) DEFAULT '/',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            ALTER TABLE site_settings ADD COLUMN IF NOT EXISTS ga_tracking_id VARCHAR(50);
            
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='site_settings' AND column_name='redirect_404_enabled') THEN
                    ALTER TABLE site_settings ADD COLUMN redirect_404_enabled BOOLEAN DEFAULT true;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='site_settings' AND column_name='redirect_404_url') THEN
                    ALTER TABLE site_settings ADD COLUMN redirect_404_url VARCHAR(500) DEFAULT '/';
                END IF;
            END $$;
            
            CREATE TABLE IF NOT EXISTS ad_settings (
                id SERIAL PRIMARY KEY,
                adsense_publisher_id VARCHAR(50),
                google_analytics_id VARCHAR(50),
                auto_ads_enabled BOOLEAN DEFAULT false,
                ad_header BOOLEAN DEFAULT false,
                ad_after_header BOOLEAN DEFAULT false,
                ad_between_games BOOLEAN DEFAULT false,
                ad_before_footer BOOLEAN DEFAULT false,
                ad_sidebar BOOLEAN DEFAULT false,
                manual_ad_code_header TEXT,
                manual_ad_code_after_header TEXT,
                manual_ad_code_between_games TEXT,
                manual_ad_code_before_footer TEXT,
                manual_ad_code_sidebar TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ad_settings' AND column_name='google_analytics_id') THEN
                    ALTER TABLE ad_settings ADD COLUMN google_analytics_id VARCHAR(50);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ad_settings' AND column_name='ads_txt_content') THEN
                    ALTER TABLE ad_settings ADD COLUMN ads_txt_content TEXT;
                END IF;
            END $$;
            
            CREATE TABLE IF NOT EXISTS daily_update_settings (
                id SERIAL PRIMARY KEY,
                enabled BOOLEAN DEFAULT false,
                post_time VARCHAR(10) DEFAULT '10:00',
                last_post_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS daily_posts (
                id SERIAL PRIMARY KEY,
                game_name VARCHAR(255) NOT NULL,
                slug VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                content TEXT,
                result VARCHAR(50),
                post_date DATE NOT NULL,
                meta_description TEXT,
                meta_keywords TEXT,
                is_published BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_name, post_date)
            );
            
            CREATE TABLE IF NOT EXISTS indexing_settings (
                id SERIAL PRIMARY KEY,
                credentials_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS manual_posts (
                id SERIAL PRIMARY KEY,
                slug VARCHAR(255) NOT NULL UNIQUE,
                title VARCHAR(500) NOT NULL,
                content TEXT,
                meta_title VARCHAR(255),
                meta_description TEXT,
                meta_keywords TEXT,
                og_title VARCHAR(255),
                og_description TEXT,
                canonical_url VARCHAR(500),
                schema_type VARCHAR(50) DEFAULT 'Article',
                is_published BOOLEAN DEFAULT false,
                publish_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database init error: {e}")

init_database()

ALLOWED_QUERY_PARAMS = {'page', 'game', 'month', 'year'}
SPAM_PARAMS = {'o', 'p', 'ref', 'fbclid', 'gclid', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'}

@app.before_request
def block_spam_query_params():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
    
    host = request.headers.get('Host', '')
    if host.startswith('www.'):
        url = request.url.replace('://www.', '://', 1)
        return redirect(url, code=301)
    
    if request.path.startswith('/_stcore/'):
        return ('', 404)
    
    allowed_txt_files = ['/robots.txt', '/ads.txt']
    if request.path in allowed_txt_files:
        pass
    else:
        blocked_extensions = ('.py', '.py.backup', '.md', '.toml', '.lock', '.gz', '.sh', '.cfg', '.ini', '.log', '.env', '.git')
        if any(request.path.endswith(ext) for ext in blocked_extensions):
            return ('', 404)
    
    blocked_paths = ['/venv/', '/.git/', '/.cache/', '/.local/', '/.streamlit/', 
                     '/.pythonlibs/', '/.upm/', '/attached_assets/', '/templates/',
                     '/__pycache__/']
    if any(request.path.startswith(bp) for bp in blocked_paths):
        return ('', 404)
    
    if request.path.startswith('/category/'):
        return ('', 410)
    
    if request.path.startswith('/api/') or request.path.startswith('/admin'):
        return None
    
    param_keys = set(request.args.keys())
    if param_keys & SPAM_PARAMS:
        return ('', 404)
    
    unknown_params = param_keys - ALLOWED_QUERY_PARAMS
    if unknown_params:
        return ('', 404)

def get_base_url():
    return request.host_url.rstrip('/').replace('http://', 'https://')

@app.route('/')
def index():
    games = get_games()
    now = get_ist_now()
    current_date = now.strftime("%d-%m-%Y")
    current_time = now.strftime("%I:%M:%S %p")
    today_date = now.strftime("%B %d, %Y")
    yesterday_date = (now - timedelta(days=1)).strftime("%B %d, %Y")
    games_with_slug = []
    for game in games:
        games_with_slug.append({
            'name': game[0],
            'time': game[1] or '--',
            'yesterday': game[2] or '--',
            'today': game[3] or '--',
            'slug': create_slug(game[0])
        })
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    daily_posts = get_daily_posts_for_display()
    base_url = get_base_url()
    return render_template('index.html', games=games_with_slug, current_date=current_date, last_update_time=current_time, today_date=today_date, yesterday_date=yesterday_date, site_settings=site_settings, ad_settings=ad_settings, daily_posts=daily_posts, base_url=base_url)

@app.route('/daily-update')
def daily_update_page():
    now = get_ist_now()
    today_date = now.strftime("%B %d, %Y")
    
    page = request.args.get('page', 1, type=int)
    per_page = 30
    
    result = get_daily_posts_paginated(page, per_page)
    
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    return render_template('daily_update.html', 
        daily_posts=result['posts'], 
        today_date=today_date, 
        site_settings=site_settings, 
        ad_settings=ad_settings,
        current_page=result['current_page'],
        total_pages=result['total_pages'],
        total_posts=result['total_posts'],
        base_url=base_url
    )

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
    
    seo_title = f"{game_name} Result Chart {month_name} {selected_year}" if game_name else "Satta King Record Chart | View All Game Results"
    seo_description = f"Check {game_name} Satta King result chart for {month_name} {selected_year}. View daily results, winning numbers, and complete record chart. Updated live with latest {game_name} results." if game_name else "View complete Satta King record charts for all games."
    seo_keywords = f"{game_name}, {game_name} result, {game_name} chart, {game_name} {month_name} {selected_year}, satta king {game_name}, {game_name} record, {game_name} live result" if game_name else "satta king, satta king chart, satta king result"
    base_url = get_base_url()
    canonical_url = f"{base_url}/chart?game={game_slug}" if game_slug else f"{base_url}/chart"
    
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
    
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
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
        faqs=faqs,
        site_settings=site_settings,
        ad_settings=ad_settings
    )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            app.permanent_session_lifetime = timedelta(days=7)
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            error = 'Invalid username or password'
    
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/privacy-policy')
def privacy_policy():
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    return render_template('static_page.html', 
        page_title="Privacy Policy",
        page_content=get_privacy_policy_content(),
        site_settings=site_settings,
        ad_settings=ad_settings,
        base_url=base_url
    )

@app.route('/about')
def about_page():
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    return render_template('static_page.html', 
        page_title="About Us",
        page_content=get_about_content(),
        site_settings=site_settings,
        ad_settings=ad_settings,
        base_url=base_url
    )

@app.route('/contact')
def contact_page():
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    return render_template('static_page.html', 
        page_title="Contact Us",
        page_content=get_contact_content(),
        site_settings=site_settings,
        ad_settings=ad_settings,
        base_url=base_url
    )

@app.route('/disclaimer')
def disclaimer_page():
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    return render_template('static_page.html', 
        page_title="Disclaimer",
        page_content=get_disclaimer_content(),
        site_settings=site_settings,
        ad_settings=ad_settings,
        base_url=base_url
    )

def get_privacy_policy_content():
    return """
    <p><strong>Effective Date:</strong> January 1, 2024 | <strong>Last Updated:</strong> February 2026</p>
    
    <p>At Satta King 786, we are committed to protecting your privacy and ensuring the security of your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you visit our website. Please read this policy carefully to understand our practices regarding your data.</p>
    
    <h2>1. Information We Collect</h2>
    
    <h3>1.1 Automatically Collected Information</h3>
    <p>When you visit our website, we automatically collect certain information about your device and browsing activity, including:</p>
    <ul>
        <li><strong>Device Information:</strong> Browser type, operating system, device type (mobile, tablet, desktop), screen resolution</li>
        <li><strong>Usage Data:</strong> Pages visited, time spent on pages, click patterns, navigation paths</li>
        <li><strong>Network Information:</strong> IP address, Internet Service Provider (ISP), approximate geographic location</li>
        <li><strong>Referral Data:</strong> The website or source that referred you to our site</li>
    </ul>
    
    <h3>1.2 Cookies and Similar Technologies</h3>
    <p>We use cookies, web beacons, and similar tracking technologies to enhance your browsing experience. These technologies help us:</p>
    <ul>
        <li>Remember your preferences and settings</li>
        <li>Understand how you interact with our website</li>
        <li>Analyze website traffic and performance</li>
        <li>Deliver personalized content and advertisements</li>
    </ul>
    
    <h2>2. How We Use Your Information</h2>
    <p>We use the collected information for the following purposes:</p>
    <ul>
        <li><strong>Service Improvement:</strong> To understand user behavior and improve our website functionality</li>
        <li><strong>Content Personalization:</strong> To deliver relevant content based on your interests</li>
        <li><strong>Analytics:</strong> To analyze traffic patterns and website performance</li>
        <li><strong>Advertising:</strong> To display relevant advertisements through third-party ad networks</li>
        <li><strong>Security:</strong> To detect and prevent fraud, abuse, and security threats</li>
        <li><strong>Legal Compliance:</strong> To comply with applicable laws and regulations</li>
    </ul>
    
    <h2>3. Third-Party Services</h2>
    
    <h3>3.1 Google Analytics</h3>
    <p>We use Google Analytics to analyze website traffic and user behavior. Google Analytics collects data through cookies and provides us with aggregated reports. You can learn more about Google's privacy practices at <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Google Privacy Policy</a>.</p>
    
    <h3>3.2 Google AdSense</h3>
    <p>We participate in Google AdSense to display advertisements. Google uses cookies to serve ads based on your prior visits to our website or other websites. You can opt out of personalized advertising by visiting <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener">Google Ads Settings</a>.</p>
    
    <h3>3.3 Other Third-Party Services</h3>
    <p>We may use additional third-party services for functionality, analytics, or advertising purposes. Each third-party service has its own privacy policy governing the use of your information.</p>
    
    <h2>4. Data Security</h2>
    <p>We implement industry-standard security measures to protect your information, including:</p>
    <ul>
        <li>Secure Socket Layer (SSL) encryption for data transmission</li>
        <li>Regular security assessments and updates</li>
        <li>Access controls and authentication mechanisms</li>
        <li>Secure data storage practices</li>
    </ul>
    <p>However, no method of transmission over the Internet or electronic storage is 100% secure. While we strive to protect your information, we cannot guarantee absolute security.</p>
    
    <h2>5. Your Rights and Choices</h2>
    <p>You have the following rights regarding your information:</p>
    <ul>
        <li><strong>Cookie Preferences:</strong> You can manage cookie settings through your browser preferences</li>
        <li><strong>Opt-Out:</strong> You can opt out of personalized advertising through industry opt-out tools</li>
        <li><strong>Do Not Track:</strong> We respect Do Not Track browser signals when applicable</li>
        <li><strong>Data Access:</strong> You may request information about the data we collect</li>
    </ul>
    
    <h2>6. Children's Privacy</h2>
    <p>Our website is not intended for children under the age of 18. We do not knowingly collect personal information from children. If you are a parent or guardian and believe your child has provided us with personal information, please contact us immediately.</p>
    
    <h2>7. Changes to This Policy</h2>
    <p>We may update this Privacy Policy from time to time to reflect changes in our practices or legal requirements. We will notify you of any material changes by posting the updated policy on this page with a new "Last Updated" date.</p>
    
    <h2>8. Contact Us</h2>
    <div class="info-box">
        <p>If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact us:</p>
        <p><strong>Email:</strong> privacy@sattaking786.com</p>
        <p><strong>Response Time:</strong> We aim to respond to all inquiries within 48 hours</p>
    </div>
    
    <p>By using our website, you acknowledge that you have read and understood this Privacy Policy and agree to its terms.</p>
    """

def get_about_content():
    return """
    <p>Welcome to <strong>Satta King 786</strong> — India's most trusted and reliable destination for live Satta King results, record charts, and daily game updates. Since our establishment in 2024, we have been serving millions of users with fast, accurate, and verified Satta King results.</p>
    
    <h2>Our Mission and Vision</h2>
    <p>Our mission is simple: to provide the fastest and most accurate Satta King results to our users. We understand the importance of timely information, which is why our dedicated team works around the clock to ensure that every result is updated within seconds of official declaration.</p>
    <p>We envision becoming the number one platform for Satta King information in India, trusted by millions for our reliability, accuracy, and user-friendly experience.</p>
    
    <h2>What We Offer</h2>
    
    <h3>Live Results</h3>
    <p>Our primary service is providing real-time Satta King results for 80+ games. Whether you're looking for Gali, Disawar, Faridabad, Ghaziabad, or any regional game, you'll find the latest results on our homepage updated throughout the day.</p>
    
    <h3>Record Charts</h3>
    <p>Access complete historical data through our comprehensive Record Chart feature. View monthly and yearly charts for any game dating back to 2024. Our charts help you analyze patterns and track results over time.</p>
    
    <h3>Daily Updates</h3>
    <p>Our Daily Update section features detailed posts for every game result. Each post includes comprehensive information about the game, result details, historical context, and analysis that helps you stay informed.</p>
    
    <h3>Mobile-Friendly Design</h3>
    <p>Access our website from any device — smartphone, tablet, or desktop. Our responsive design ensures a seamless experience regardless of screen size, making it easy to check results on the go.</p>
    
    <h2>Games We Cover</h2>
    <p>Our comprehensive coverage includes all major Satta King games across India:</p>
    <ul>
        <li><strong>Popular Games:</strong> Gali, Disawar, Faridabad, Ghaziabad, Delhi Bazaar</li>
        <li><strong>Satta Matka:</strong> Kalyan Matka, Mumbai Matka, Rajdhani Day/Night</li>
        <li><strong>Regional Games:</strong> UP Satta King, Black Satta, Shri Ganesh, Taj, Play Bazaar</li>
        <li><strong>Special Games:</strong> Desawar, Sridevi, Madhur Day/Night, Time Bazaar</li>
        <li><strong>Other Games:</strong> And 70+ more games updated daily</li>
    </ul>
    
    <h2>Why Choose Satta King 786?</h2>
    <div class="info-box">
        <ul>
            <li><strong>Speed:</strong> Results updated within seconds of official declaration</li>
            <li><strong>Accuracy:</strong> Every result is verified before publishing</li>
            <li><strong>Reliability:</strong> 24/7 availability with minimal downtime</li>
            <li><strong>Free Access:</strong> No registration, no fees, no hidden charges</li>
            <li><strong>History:</strong> Complete record charts from 2024 to present</li>
            <li><strong>User-Friendly:</strong> Clean interface designed for easy navigation</li>
        </ul>
    </div>
    
    <h2>Our Team</h2>
    <p>Behind Satta King 786 is a dedicated team of professionals who are passionate about delivering the best service to our users. Our team includes:</p>
    <ul>
        <li><strong>Result Updaters:</strong> Working in shifts to ensure 24/7 coverage</li>
        <li><strong>Content Writers:</strong> Creating informative daily updates</li>
        <li><strong>Technical Team:</strong> Maintaining website performance and security</li>
        <li><strong>Support Staff:</strong> Responding to user queries and feedback</li>
    </ul>
    
    <h2>Our Commitment to Quality</h2>
    <p>We are committed to maintaining the highest standards of quality in everything we do:</p>
    <ul>
        <li>Every result is cross-verified from multiple sources before publishing</li>
        <li>Our website is regularly updated with the latest security measures</li>
        <li>We continuously improve our user interface based on feedback</li>
        <li>We maintain transparency in all our operations</li>
    </ul>
    
    <h2>Contact Information</h2>
    <p>We value your feedback and suggestions. If you have any questions, concerns, or ideas for improvement, please don't hesitate to reach out to us through our <a href="/contact">Contact page</a>.</p>
    
    <p>Thank you for choosing Satta King 786. We are honored to serve you and committed to being your trusted source for Satta King results.</p>
    """

def get_contact_content():
    return """
    <p>We value your feedback and are committed to providing excellent support to all our users. Whether you have a question, suggestion, or concern, we're here to help. Please use the information below to get in touch with us.</p>
    
    <h2>Get in Touch</h2>
    <div class="info-box">
        <p><strong>Email Support:</strong> support@sattaking786.com</p>
        <p><strong>General Inquiries:</strong> info@sattaking786.com</p>
        <p><strong>Technical Issues:</strong> tech@sattaking786.com</p>
        <p><strong>Response Time:</strong> We typically respond within 24-48 hours on business days</p>
        <p><strong>Working Hours:</strong> Monday to Sunday, 9:00 AM to 11:00 PM IST</p>
    </div>
    
    <h2>How We Can Help</h2>
    <p>Our support team can assist you with:</p>
    <ul>
        <li><strong>Result Verification:</strong> Questions about specific game results</li>
        <li><strong>Website Navigation:</strong> Help finding features or information</li>
        <li><strong>Technical Issues:</strong> Problems accessing the website or viewing results</li>
        <li><strong>Chart Queries:</strong> Questions about record charts and historical data</li>
        <li><strong>Feedback:</strong> Suggestions for improving our services</li>
        <li><strong>Error Reporting:</strong> Reporting incorrect information or bugs</li>
    </ul>
    
    <h2>Frequently Asked Questions</h2>
    
    <h3>About Results</h3>
    <p><strong>Q: How quickly are results updated?</strong></p>
    <p>A: Our results are updated in real-time, typically within seconds of official declaration. We have a dedicated team monitoring results throughout the day.</p>
    
    <p><strong>Q: What if I see "--" instead of a result?</strong></p>
    <p>A: The "--" symbol indicates that the game result has not been declared yet. Please check back at the scheduled game time or refresh the page.</p>
    
    <p><strong>Q: Are all results verified?</strong></p>
    <p>A: Yes, every result is cross-verified from multiple reliable sources before being published on our website.</p>
    
    <h3>About Record Charts</h3>
    <p><strong>Q: How far back do your record charts go?</strong></p>
    <p>A: Our record charts contain historical data from January 2024 to the present. We continuously update our database with new results.</p>
    
    <p><strong>Q: How do I view a specific game's chart?</strong></p>
    <p>A: Visit the <a href="/chart">Record Chart</a> page, select your desired game from the dropdown menu, choose the month and year, and click "View Chart".</p>
    
    <h3>About Our Website</h3>
    <p><strong>Q: Is the website free to use?</strong></p>
    <p>A: Absolutely! Our website is completely free with no registration, no subscription, and no hidden charges.</p>
    
    <p><strong>Q: Can I access the website on my mobile phone?</strong></p>
    <p>A: Yes, our website is fully responsive and optimized for all devices including smartphones, tablets, and desktop computers.</p>
    
    <p><strong>Q: How often is the website updated?</strong></p>
    <p>A: Results are updated throughout the day as games are declared. Our Daily Update posts are published regularly with comprehensive game information.</p>
    
    <h2>Report an Issue</h2>
    <p>Found an error or technical problem? We appreciate your help in keeping our website accurate and functional. When reporting an issue, please include:</p>
    <ul>
        <li>The date and time when you noticed the issue</li>
        <li>The specific page or game affected</li>
        <li>A description of the problem</li>
        <li>Screenshots if possible</li>
        <li>Your device and browser information</li>
    </ul>
    
    <h2>Feedback and Suggestions</h2>
    <p>We're always looking to improve our services. If you have ideas for new features, improvements, or content suggestions, we'd love to hear from you. Your feedback helps us serve you better.</p>
    
    <div class="warning-box">
        <p><strong>Note:</strong> We do not provide any tips, predictions, or leak numbers. Please do not contact us for such requests. We are strictly an informational website providing result updates only.</p>
    </div>
    
    <p>Thank you for choosing Satta King 786. We look forward to hearing from you!</p>
    """

def get_disclaimer_content():
    return """
    <p><strong>Effective Date:</strong> January 1, 2024 | <strong>Last Updated:</strong> February 2026</p>
    
    <p>Please read this disclaimer carefully before using Satta King 786 website. By accessing or using our website, you agree to be bound by the terms and conditions outlined in this disclaimer. If you do not agree with any part of this disclaimer, please do not use our website.</p>
    
    <h2>1. Nature of Website</h2>
    <p>Satta King 786 is an <strong>informational website only</strong>. We provide historical results, charts, and data related to various Satta King games for informational and entertainment purposes. Our website serves as a repository of publicly available information compiled for user convenience.</p>
    
    <h2>2. No Promotion of Gambling</h2>
    <div class="warning-box">
        <p><strong>IMPORTANT:</strong> We do not encourage, promote, facilitate, or endorse any form of gambling, betting, lottery, or any illegal activities. This website is strictly for informational purposes. We do not provide:</p>
    </div>
    <ul>
        <li>Tips, predictions, or "leak" numbers</li>
        <li>Betting services or platforms</li>
        <li>Money transactions or payment services</li>
        <li>Any form of gambling assistance</li>
    </ul>
    
    <h2>3. Legal Compliance</h2>
    <p>Gambling laws vary significantly across different states and countries. It is your sole responsibility to:</p>
    <ul>
        <li>Understand and comply with the laws applicable in your jurisdiction</li>
        <li>Verify the legality of any activity before participating</li>
        <li>Accept full responsibility for your actions</li>
    </ul>
    <p>We are not responsible for any legal consequences arising from your use of information on this website. If gambling is illegal in your area, please do not participate in any such activities.</p>
    
    <h2>4. Accuracy of Information</h2>
    <p>While we make every effort to ensure the accuracy of information on our website:</p>
    <ul>
        <li>We do not guarantee 100% accuracy of any result or data</li>
        <li>Information may contain errors, omissions, or outdated data</li>
        <li>Results should be verified from official sources</li>
        <li>We are not liable for any losses resulting from inaccurate information</li>
    </ul>
    
    <h2>5. No Warranties</h2>
    <p>This website is provided "as is" without any representations or warranties, express or implied. We make no warranties regarding:</p>
    <ul>
        <li>The completeness or accuracy of information</li>
        <li>The availability or uninterrupted access to the website</li>
        <li>The absence of viruses or other harmful components</li>
        <li>The fitness for any particular purpose</li>
    </ul>
    
    <h2>6. Limitation of Liability</h2>
    <p>To the fullest extent permitted by law, Satta King 786, its owners, operators, employees, and affiliates shall not be liable for:</p>
    <ul>
        <li>Any direct, indirect, incidental, or consequential damages</li>
        <li>Loss of profits, data, or business opportunities</li>
        <li>Any harm arising from the use or inability to use this website</li>
        <li>Any actions taken based on information provided on this website</li>
    </ul>
    
    <h2>7. Third-Party Links</h2>
    <p>Our website may contain links to third-party websites. These links are provided for convenience only. We do not:</p>
    <ul>
        <li>Endorse or control third-party content</li>
        <li>Accept responsibility for third-party websites</li>
        <li>Guarantee the accuracy of third-party information</li>
    </ul>
    
    <h2>8. Age Restriction</h2>
    <div class="warning-box">
        <p>This website is intended for users who are <strong>18 years of age or older</strong>. By using this website, you confirm that you are at least 18 years old. Minors are strictly prohibited from accessing this website.</p>
    </div>
    
    <h2>9. Responsible Gaming</h2>
    <p>If you choose to participate in any form of gaming or gambling (where legal):</p>
    <ul>
        <li><strong>Set limits:</strong> Decide how much time and money you can afford before you start</li>
        <li><strong>Never chase losses:</strong> Accept that losing is part of the game</li>
        <li><strong>Don't borrow:</strong> Never gamble with borrowed money</li>
        <li><strong>Take breaks:</strong> Regular breaks help maintain perspective</li>
        <li><strong>Seek help:</strong> If you feel you have a problem, professional help is available</li>
    </ul>
    
    <h2>10. Changes to Disclaimer</h2>
    <p>We reserve the right to modify this disclaimer at any time without prior notice. Changes will be effective immediately upon posting. Your continued use of the website after any changes constitutes acceptance of the modified disclaimer.</p>
    
    <h2>11. Governing Law</h2>
    <p>This disclaimer shall be governed by and construed in accordance with the laws of India. Any disputes shall be subject to the exclusive jurisdiction of the courts in India.</p>
    
    <h2>12. Contact</h2>
    <p>If you have any questions about this disclaimer, please contact us through our <a href="/contact">Contact page</a>.</p>
    
    <div class="info-box">
        <p><strong>Remember:</strong> This website is for informational purposes only. We strongly advise against any form of gambling. If you choose to engage in such activities, please do so responsibly and in compliance with your local laws.</p>
    </div>
    """

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

def get_daily_update_settings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, enabled, post_time, last_post_date FROM daily_update_settings LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                'id': row[0],
                'enabled': row[1],
                'post_time': row[2],
                'last_post_date': str(row[3]) if row[3] else None
            }
        return {'enabled': False, 'post_time': '10:00', 'last_post_date': None}
    except:
        return {'enabled': False, 'post_time': '10:00', 'last_post_date': None}

def generate_seo_post_content(game_name, result, post_date):
    date_str = post_date.strftime("%d %B %Y")
    day_num = post_date.day
    month_name = post_date.strftime("%B")
    year = post_date.strftime("%Y")
    game_slug = create_slug(game_name)
    
    result_display = result if result and result != '--' else 'Waiting...'
    is_waiting = result_display == 'Waiting...'
    
    slug = f"{game_slug}-result-{day_num}-{month_name}-{year}"
    
    title = f"{game_name} Satta Result {date_str}"
    
    meta_description = f"{game_name} Satta result {date_str} - Check today's {game_name} winning number, live result update, and {month_name} {year} record chart. Fast and verified {game_name} Satta King result."
    
    meta_keywords = f"{game_name} result, {game_name} result today, {game_name} satta result, {game_name} satta king, {game_name} {date_str}, {game_name} result {month_name} {year}, {game_name} chart, {game_name} record chart {year}, {game_name} live result, satta king {game_name} today, {game_name} winning number, {game_name} result chart"
    
    status_text = result_display if not is_waiting else 'Pending'
    
    common_content = f"""
    <h2 class="section-title">{game_name} Game Details</h2>
    <div class="info-grid">
        <div class="info-item">
            <div class="info-item-label">Game Name</div>
            <div class="info-item-value">{game_name}</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Result Date</div>
            <div class="info-item-value">{date_str}</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Result Month</div>
            <div class="info-item-value">{month_name} {year}</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Result Status</div>
            <div class="info-item-value">{status_text}</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Game Type</div>
            <div class="info-item-value">Satta King</div>
        </div>
        <div class="info-item">
            <div class="info-item-label">Update Frequency</div>
            <div class="info-item-value">Daily</div>
        </div>
    </div>

    <h2 class="section-title">{game_name} Result Chart {month_name} {year}</h2>
    <div class="post-text">
        <p>View the complete {game_name} monthly record chart to analyze past results and track all winning numbers for {month_name} {year}.</p>
    </div>
    <a href="/chart?game={game_slug}" class="chart-link-card">
        <div class="chart-link-icon">📊</div>
        <div>
            <div class="chart-link-text">{game_name} Record Chart - {month_name} {year}</div>
            <div class="chart-link-sub">View complete daily results and winning number history</div>
        </div>
    </a>

    <h2 class="section-title">About {game_name}</h2>
    <div class="post-text">
        <p>{game_name} is one of the most popular Satta King games in India. Every day, thousands of players check the {game_name} result on our website. We provide fast, accurate, and verified {game_name} results as soon as they are officially declared.</p>
        <p>The {game_name} game operates on a fixed schedule with daily result declarations. Our platform ensures you get the {game_name} result without any delay, directly from authentic sources.</p>
    </div>

    <h2 class="section-title">Why Choose Us for {game_name} Result?</h2>
    <div class="features-grid">
        <div class="feature-card">
            <div class="feature-card-title">⚡ Fastest Updates</div>
            <div class="feature-card-desc">{game_name} results updated within seconds of official declaration</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">✅ 100% Verified</div>
            <div class="feature-card-desc">All {game_name} results verified from authentic sources</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">📊 Complete History</div>
            <div class="feature-card-desc">Access {game_name} record charts for any month and year</div>
        </div>
        <div class="feature-card">
            <div class="feature-card-title">📱 Mobile Friendly</div>
            <div class="feature-card-desc">Check {game_name} results easily on any device</div>
        </div>
    </div>

    <h2 class="section-title">How to Check {game_name} Result</h2>
    <div class="post-text">
        <ul>
            <li>Visit our website daily at the scheduled time for live {game_name} result</li>
            <li>Check the {game_name} Record Chart for complete historical data</li>
            <li>Bookmark this page for quick access to daily {game_name} updates</li>
            <li>All results are verified before publishing on our website</li>
            <li>Check previous day results from our archive anytime</li>
        </ul>
    </div>

    <h2 class="section-title">Frequently Asked Questions</h2>
    <div class="faq-item active">
        <div class="faq-question">What is today's {game_name} result? <span class="faq-arrow">▼</span></div>
        <div class="faq-answer">The {game_name} result for {date_str} is {result_display}. This result is verified and confirmed from authentic sources.</div>
    </div>
    <div class="faq-item">
        <div class="faq-question">What time does {game_name} result come? <span class="faq-arrow">▼</span></div>
        <div class="faq-answer">{game_name} result is declared daily at the scheduled game time. Check our homepage to see the exact timing for {game_name}.</div>
    </div>
    <div class="faq-item">
        <div class="faq-question">Where can I check {game_name} result chart? <span class="faq-arrow">▼</span></div>
        <div class="faq-answer">Visit our <a href="/chart?game={game_slug}">{game_name} Record Chart</a> page where you can view results for any month and year. Select the month and year from the dropdown to view complete historical results.</div>
    </div>
    <div class="faq-item">
        <div class="faq-question">Is this {game_name} result accurate? <span class="faq-arrow">▼</span></div>
        <div class="faq-answer">Yes, we provide 100% verified and accurate {game_name} results. Our platform is trusted by thousands of daily visitors and all results are cross-checked before publishing.</div>
    </div>

    <h2 class="section-title">Related Games</h2>
    <div class="post-text">
        <p>We also provide live results for other popular Satta King games including Gali, Disawar, Faridabad, Ghaziabad, and many more. Visit our <a href="/" style="color: #1a73e8; font-weight: 600;">homepage</a> for the complete list of games and their latest results.</p>
    </div>

    <div class="disclaimer-box">
        This website is for informational and entertainment purposes only. We do not encourage or facilitate any form of gambling. Please check your local laws before engaging in any activities. Always act responsibly.
    </div>
"""
    
    if is_waiting:
        content = f"""
    <div class="result-card waiting">
        <div class="result-card-label">{game_name} Result - {date_str}</div>
        <div class="result-card-value">Waiting...</div>
        <div class="result-card-note">Result will be updated as soon as it is declared</div>
        <span class="result-card-badge">⏳ Awaiting Result</span>
    </div>
    {common_content}
"""
    else:
        content = f"""
    <div class="result-card declared">
        <div class="result-card-label">{game_name} Result - {date_str}</div>
        <div class="result-card-value">{result_display}</div>
        <div class="result-card-note">Verified winning number for {date_str}</div>
        <span class="result-card-badge">✅ Result Declared</span>
    </div>
    {common_content}
"""
    
    return {
        'slug': slug,
        'title': title,
        'content': content,
        'meta_description': meta_description,
        'meta_keywords': meta_keywords,
        'result': result_display
    }

def create_daily_posts():
    try:
        today = get_ist_now().date()
        games = get_games()
        conn = get_db_connection()
        cur = conn.cursor()
        
        for game in games:
            game_name = game[0]
            today_result = game[3] if game[3] else '--'
            
            post_data = generate_seo_post_content(game_name, today_result, today)
            
            cur.execute("""
                INSERT INTO daily_posts (game_name, slug, title, content, result, post_date, meta_description, meta_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (game_name, post_date) 
                DO UPDATE SET content = EXCLUDED.content, result = EXCLUDED.result, title = EXCLUDED.title, 
                              meta_description = EXCLUDED.meta_description, meta_keywords = EXCLUDED.meta_keywords,
                              updated_at = CURRENT_TIMESTAMP
            """, (game_name, post_data['slug'], post_data['title'], post_data['content'], 
                  post_data['result'], today, post_data['meta_description'], post_data['meta_keywords']))
        
        cur.execute("""
            UPDATE daily_update_settings SET last_post_date = %s WHERE id = (SELECT id FROM daily_update_settings LIMIT 1)
        """, (today,))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Daily posts created/updated for {len(games)} games on {today}")
        return True
    except Exception as e:
        print(f"Error creating daily posts: {e}")
        return False

def update_daily_posts_results():
    try:
        today = get_ist_now().date()
        games = get_games()
        conn = get_db_connection()
        cur = conn.cursor()
        
        for game in games:
            game_name = game[0]
            today_result = game[3] if game[3] else '--'
            
            if today_result and today_result != '--':
                post_data = generate_seo_post_content(game_name, today_result, today)
                cur.execute("""
                    UPDATE daily_posts SET content = %s, result = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE game_name = %s AND post_date = %s
                """, (post_data['content'], post_data['result'], game_name, today))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating daily posts: {e}")
        return False

def create_posts_from_historical(game_name, limit=100):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT game_name, result_date, result FROM game_results 
            WHERE game_name = %s
            ORDER BY result_date DESC
            LIMIT %s
        """, (game_name, limit))
        results = cur.fetchall()
        
        created = 0
        skipped = 0
        
        for row in results:
            g_name, result_date, result = row
            if result and result != '--' and result != 'XX':
                post_data = generate_seo_post_content(g_name, result, result_date)
                
                cur.execute("""
                    INSERT INTO daily_posts (game_name, slug, title, content, result, post_date, meta_description, meta_keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (game_name, post_date) DO NOTHING
                """, (g_name, post_data['slug'], post_data['title'], post_data['content'], 
                      post_data['result'], result_date, post_data['meta_description'], post_data['meta_keywords']))
                
                if cur.rowcount > 0:
                    created += 1
                else:
                    skipped += 1
        
        conn.commit()
        cur.close()
        conn.close()
        return {'created': created, 'skipped': skipped}
    except Exception as e:
        print(f"Error creating posts from historical: {e}")
        return {'created': 0, 'skipped': 0, 'error': str(e)}

def setup_daily_post_scheduler():
    settings = get_daily_update_settings()
    try:
        if scheduler.get_job('daily_post'):
            scheduler.remove_job('daily_post')
        if scheduler.get_job('update_post_results'):
            scheduler.remove_job('update_post_results')
        
        if settings.get('enabled'):
            post_time = settings.get('post_time', '10:00')
            hour, minute = map(int, post_time.split(':'))
            
            scheduler.add_job(
                create_daily_posts,
                trigger='cron',
                hour=hour,
                minute=minute,
                timezone=IST,
                id='daily_post',
                replace_existing=True
            )
            
            scheduler.add_job(
                update_daily_posts_results,
                trigger='interval',
                minutes=5,
                id='update_post_results',
                replace_existing=True
            )
            print(f"Daily post scheduler enabled at {post_time} IST")
    except Exception as e:
        print(f"Error setting up daily post scheduler: {e}")

@app.route('/api/daily-update-settings', methods=['GET'])
def api_get_daily_update_settings():
    return jsonify(get_daily_update_settings())

@app.route('/api/daily-update-settings', methods=['POST'])
def api_update_daily_update_settings():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM daily_update_settings LIMIT 1")
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""
                UPDATE daily_update_settings SET enabled=%s, post_time=%s WHERE id=%s
            """, (data.get('enabled', False), data.get('post_time', '10:00'), existing[0]))
        else:
            cur.execute("""
                INSERT INTO daily_update_settings (enabled, post_time)
                VALUES (%s, %s)
            """, (data.get('enabled', False), data.get('post_time', '10:00')))
        
        conn.commit()
        cur.close()
        conn.close()
        
        setup_daily_post_scheduler()
        
        return jsonify({'message': 'Settings saved', 'enabled': data.get('enabled'), 'post_time': data.get('post_time')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_daily_posts_for_display():
    try:
        today = get_ist_now().date()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, game_name, slug, title, result, post_date, created_at, meta_description 
            FROM daily_posts 
            WHERE post_date = %s AND is_published = true
            ORDER BY created_at DESC
        """, (today,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        posts = []
        for row in rows:
            posts.append({
                'id': row[0],
                'game_name': row[1],
                'slug': row[2],
                'title': row[3],
                'result': row[4],
                'post_date': str(row[5]),
                'created_at': str(row[6]),
                'description': row[7][:120] + '...' if row[7] and len(row[7]) > 120 else (row[7] or '')
            })
        return posts
    except Exception as e:
        return []

def get_daily_posts_paginated(page=1, per_page=30):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM daily_posts WHERE is_published = true")
        total_posts = cur.fetchone()[0]
        
        total_pages = max(1, (total_posts + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page
        
        cur.execute("""
            SELECT id, game_name, slug, title, result, post_date, created_at, meta_description 
            FROM daily_posts 
            WHERE is_published = true
            ORDER BY post_date DESC, created_at DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        posts = []
        for row in rows:
            posts.append({
                'id': row[0],
                'game_name': row[1],
                'slug': row[2],
                'title': row[3],
                'result': row[4],
                'post_date': str(row[5]),
                'created_at': str(row[6]),
                'description': row[7][:120] + '...' if row[7] and len(row[7]) > 120 else (row[7] or '')
            })
        
        return {
            'posts': posts,
            'current_page': page,
            'total_pages': total_pages,
            'total_posts': total_posts
        }
    except Exception as e:
        return {'posts': [], 'current_page': 1, 'total_pages': 1, 'total_posts': 0}

@app.route('/api/daily-posts', methods=['GET'])
def api_get_daily_posts():
    try:
        posts = get_daily_posts_for_display()
        return jsonify(posts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-daily-posts', methods=['POST'])
def api_create_daily_posts():
    try:
        create_daily_posts()
        return jsonify({'message': 'Daily posts created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create-historical-posts', methods=['POST'])
def api_create_historical_posts():
    try:
        data = request.json
        game_index = data.get('game_index', 0)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT game_name FROM game_results ORDER BY game_name")
        all_games = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        
        if game_index >= len(all_games):
            return jsonify({'done': True, 'total_created': 0, 'message': 'All games processed'})
        
        game_name = all_games[game_index]
        result = create_posts_from_historical(game_name, limit=500)
        
        return jsonify({
            'done': game_index + 1 >= len(all_games),
            'game_index': game_index,
            'game_name': game_name,
            'created': result.get('created', 0),
            'skipped': result.get('skipped', 0),
            'total_games': len(all_games),
            'success': True
        })
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/<slug>')
def view_post(slug):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, game_name, slug, title, content, result, post_date, meta_description, meta_keywords
            FROM daily_posts WHERE slug = %s AND is_published = true
        """, (slug,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return "Post not found", 404
        
        post = {
            'id': row[0],
            'game_name': row[1],
            'slug': row[2],
            'title': row[3],
            'content': row[4],
            'result': row[5],
            'post_date': row[6],
            'meta_description': row[7],
            'meta_keywords': row[8]
        }
        
        site_settings = get_site_settings()
        ad_settings = get_ad_settings()
        base_url = get_base_url()
        return render_template('post.html', post=post, site_settings=site_settings, ad_settings=ad_settings, base_url=base_url)
    except Exception as e:
        return f"Error: {e}", 500

setup_daily_post_scheduler()

def get_site_settings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, logo_data, favicon_data, site_title, ga_tracking_id, redirect_404_enabled, redirect_404_url FROM site_settings LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                'id': row[0],
                'logo_data': row[1],
                'favicon_data': row[2],
                'site_title': row[3],
                'ga_tracking_id': row[4],
                'redirect_404_enabled': row[5] if row[5] is not None else True,
                'redirect_404_url': row[6] if row[6] else '/'
            }
        return {'logo_data': None, 'favicon_data': None, 'site_title': 'Satta King', 'ga_tracking_id': None, 'redirect_404_enabled': True, 'redirect_404_url': '/'}
    except:
        return {'logo_data': None, 'favicon_data': None, 'site_title': 'Satta King', 'ga_tracking_id': None, 'redirect_404_enabled': True, 'redirect_404_url': '/'}

@app.route('/api/site-settings', methods=['GET'])
def api_get_site_settings():
    return jsonify(get_site_settings())

@app.route('/api/site-settings', methods=['POST'])
def api_update_site_settings():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM site_settings LIMIT 1")
        existing = cur.fetchone()
        
        if existing:
            updates = []
            values = []
            if 'logo_data' in data:
                updates.append("logo_data = %s")
                values.append(data['logo_data'])
            if 'favicon_data' in data:
                updates.append("favicon_data = %s")
                values.append(data['favicon_data'])
            if 'site_title' in data:
                updates.append("site_title = %s")
                values.append(data['site_title'])
            if 'ga_tracking_id' in data:
                updates.append("ga_tracking_id = %s")
                values.append(data['ga_tracking_id'] if data['ga_tracking_id'] else None)
            updates.append("updated_at = %s")
            values.append(get_ist_now())
            values.append(existing[0])
            
            cur.execute(f"UPDATE site_settings SET {', '.join(updates)} WHERE id = %s", values)
        else:
            cur.execute("""
                INSERT INTO site_settings (logo_data, favicon_data, site_title, ga_tracking_id, updated_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (data.get('logo_data'), data.get('favicon_data'), data.get('site_title', 'Satta King'), data.get('ga_tracking_id'), get_ist_now()))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Settings saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_ad_settings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT adsense_publisher_id, auto_ads_enabled, ad_header, ad_after_header, 
                       ad_between_games, ad_before_footer, ad_sidebar, manual_ad_code_header,
                       manual_ad_code_after_header, manual_ad_code_between_games, 
                       manual_ad_code_before_footer, manual_ad_code_sidebar, google_analytics_id, ads_txt_content FROM ad_settings LIMIT 1""")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {
                'adsense_publisher_id': row[0],
                'auto_ads_enabled': row[1],
                'ad_header': row[2],
                'ad_after_header': row[3],
                'ad_between_games': row[4],
                'ad_before_footer': row[5],
                'ad_sidebar': row[6],
                'manual_ad_code_header': row[7],
                'manual_ad_code_after_header': row[8],
                'manual_ad_code_between_games': row[9],
                'manual_ad_code_before_footer': row[10],
                'manual_ad_code_sidebar': row[11],
                'google_analytics_id': row[12],
                'ads_txt_content': row[13]
            }
        return {}
    except:
        return {}

@app.route('/api/ad-settings', methods=['GET'])
def api_get_ad_settings():
    return jsonify(get_ad_settings())

@app.route('/api/ad-settings', methods=['POST'])
def api_save_ad_settings():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM ad_settings LIMIT 1")
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""UPDATE ad_settings SET 
                adsense_publisher_id = %s, auto_ads_enabled = %s,
                ad_header = %s, ad_after_header = %s, ad_between_games = %s,
                ad_before_footer = %s, ad_sidebar = %s,
                manual_ad_code_header = %s, manual_ad_code_after_header = %s,
                manual_ad_code_between_games = %s, manual_ad_code_before_footer = %s,
                manual_ad_code_sidebar = %s, google_analytics_id = %s, ads_txt_content = %s, updated_at = %s WHERE id = %s""",
                (data.get('adsense_publisher_id'), data.get('auto_ads_enabled', False),
                 data.get('ad_header', False), data.get('ad_after_header', False),
                 data.get('ad_between_games', False), data.get('ad_before_footer', False),
                 data.get('ad_sidebar', False), data.get('manual_ad_code_header'),
                 data.get('manual_ad_code_after_header'), data.get('manual_ad_code_between_games'),
                 data.get('manual_ad_code_before_footer'), data.get('manual_ad_code_sidebar'),
                 data.get('google_analytics_id'), data.get('ads_txt_content'), get_ist_now(), existing[0]))
        else:
            cur.execute("""INSERT INTO ad_settings (adsense_publisher_id, auto_ads_enabled,
                ad_header, ad_after_header, ad_between_games, ad_before_footer, ad_sidebar,
                manual_ad_code_header, manual_ad_code_after_header, manual_ad_code_between_games,
                manual_ad_code_before_footer, manual_ad_code_sidebar, google_analytics_id, ads_txt_content, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (data.get('adsense_publisher_id'), data.get('auto_ads_enabled', False),
                 data.get('ad_header', False), data.get('ad_after_header', False),
                 data.get('ad_between_games', False), data.get('ad_before_footer', False),
                 data.get('ad_sidebar', False), data.get('manual_ad_code_header'),
                 data.get('manual_ad_code_after_header'), data.get('manual_ad_code_between_games'),
                 data.get('manual_ad_code_before_footer'), data.get('manual_ad_code_sidebar'),
                 data.get('google_analytics_id'), data.get('ads_txt_content'), get_ist_now()))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Ad settings saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manual-posts', methods=['GET'])
def api_get_manual_posts():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, title, is_published, created_at 
            FROM manual_posts 
            ORDER BY created_at DESC
        """)
        posts = [{'id': r[0], 'slug': r[1], 'title': r[2], 'is_published': r[3], 'created_at': str(r[4])} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify(posts)
    except Exception as e:
        return jsonify([])

@app.route('/api/manual-posts/<int:id>', methods=['GET'])
def api_get_manual_post(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, title, content, meta_title, meta_description, meta_keywords,
                   og_title, og_description, canonical_url, schema_type, is_published
            FROM manual_posts WHERE id = %s
        """, (id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return jsonify({
                'id': row[0], 'slug': row[1], 'title': row[2], 'content': row[3],
                'meta_title': row[4], 'meta_description': row[5], 'meta_keywords': row[6],
                'og_title': row[7], 'og_description': row[8], 'canonical_url': row[9],
                'schema_type': row[10], 'is_published': row[11]
            })
        return jsonify({'error': 'Post not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manual-posts', methods=['POST'])
def api_create_manual_post():
    try:
        data = request.json
        if not data.get('title') or not data.get('slug'):
            return jsonify({'success': False, 'error': 'Title and slug are required'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM manual_posts WHERE slug = %s", (data.get('slug'),))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': 'A post with this slug already exists'}), 400
        cur.execute("""
            INSERT INTO manual_posts (slug, title, content, meta_title, meta_description, meta_keywords,
                                      og_title, og_description, canonical_url, schema_type, is_published, publish_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('slug'), data.get('title'), data.get('content'),
            data.get('meta_title'), data.get('meta_description'), data.get('meta_keywords'),
            data.get('og_title'), data.get('og_description'), data.get('canonical_url'),
            data.get('schema_type', 'Article'), data.get('is_published', False),
            get_ist_now() if data.get('is_published') else None
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/manual-posts/<int:id>', methods=['PUT'])
def api_update_manual_post(id):
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE manual_posts SET 
                slug = %s, title = %s, content = %s, meta_title = %s, meta_description = %s,
                meta_keywords = %s, og_title = %s, og_description = %s, canonical_url = %s,
                schema_type = %s, is_published = %s, updated_at = %s,
                publish_date = CASE WHEN %s AND publish_date IS NULL THEN %s ELSE publish_date END
            WHERE id = %s
        """, (
            data.get('slug'), data.get('title'), data.get('content'),
            data.get('meta_title'), data.get('meta_description'), data.get('meta_keywords'),
            data.get('og_title'), data.get('og_description'), data.get('canonical_url'),
            data.get('schema_type', 'Article'), data.get('is_published', False), get_ist_now(),
            data.get('is_published'), get_ist_now(), id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/manual-posts/<int:id>', methods=['DELETE'])
def api_delete_manual_post(id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM manual_posts WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_manual_posts_published():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, title, content, meta_description, publish_date 
            FROM manual_posts 
            WHERE is_published = true 
            ORDER BY publish_date DESC
        """)
        posts = [{
            'id': r[0], 'slug': r[1], 'title': r[2], 'content': r[3],
            'meta_description': r[4], 'publish_date': r[5]
        } for r in cur.fetchall()]
        cur.close()
        conn.close()
        return posts
    except:
        return []

@app.route('/latest')
def latest_page():
    posts = get_manual_posts_published()
    site_settings = get_site_settings()
    ad_settings = get_ad_settings()
    base_url = get_base_url()
    now = get_ist_now()
    return render_template('latest.html',
                         posts=posts,
                         site_settings=site_settings,
                         ad_settings=ad_settings,
                         base_url=base_url,
                         current_date=now.strftime("%d-%m-%Y"),
                         current_time=now.strftime("%I:%M:%S %p"))

@app.route('/latest/<slug>')
def manual_post_page(slug):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, slug, title, content, meta_title, meta_description, meta_keywords,
                   og_title, og_description, canonical_url, schema_type, publish_date
            FROM manual_posts 
            WHERE slug = %s AND is_published = true
        """, (slug,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            post = {
                'id': row[0], 'slug': row[1], 'title': row[2], 'content': row[3],
                'meta_title': row[4] or row[2], 'meta_description': row[5],
                'meta_keywords': row[6], 'og_title': row[7] or row[2],
                'og_description': row[8] or row[5], 'canonical_url': row[9],
                'schema_type': row[10] or 'Article', 'publish_date': row[11]
            }
            site_settings = get_site_settings()
            ad_settings = get_ad_settings()
            base_url = get_base_url()
            return render_template('manual_post.html', post=post, site_settings=site_settings, ad_settings=ad_settings, base_url=base_url)
        return redirect('/latest')
    except:
        return redirect('/latest')

def get_indexing_credentials():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT credentials_json FROM indexing_settings ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row[0] if row else None
    except:
        return None

@app.route('/api/indexing/status')
@login_required
def api_indexing_status():
    creds = get_indexing_credentials()
    return jsonify({'configured': creds is not None})

@app.route('/api/indexing/save-credentials', methods=['POST'])
@login_required
def api_save_indexing_credentials():
    try:
        data = request.get_json()
        creds_json = data.get('credentials_json', '')
        try:
            json.loads(creds_json)
        except:
            return jsonify({'success': False, 'error': 'Invalid JSON format'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM indexing_settings ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE indexing_settings SET credentials_json = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (creds_json, row[0]))
        else:
            cur.execute("INSERT INTO indexing_settings (credentials_json) VALUES (%s)", (creds_json,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/indexing/submit-urls', methods=['POST'])
@login_required
def api_submit_indexing_urls():
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        from googleapiclient.discovery import build
        data = request.get_json()
        urls = data.get('urls', [])
        action = data.get('action', 'URL_UPDATED')
        if action not in ('URL_UPDATED', 'URL_DELETED'):
            return jsonify({'success': False, 'error': 'Invalid action type'}), 400
        if not urls:
            return jsonify({'success': False, 'error': 'No URLs provided'}), 400
        creds_json = get_indexing_credentials()
        if not creds_json:
            return jsonify({'success': False, 'error': 'Google credentials not configured'}), 400
        SCOPES = ['https://www.googleapis.com/auth/indexing']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scopes=SCOPES)
        service = build('indexing', 'v3', credentials=credentials)
        results = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
            try:
                result = service.urlNotifications().publish(body={'url': url, 'type': action}).execute()
                results.append({'url': url, 'status': 'success', 'response': str(result)})
            except Exception as e:
                results.append({'url': url, 'status': 'error', 'error': str(e)})
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/indexing/auto-submit', methods=['POST'])
@login_required
def api_auto_submit_indexing():
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        from googleapiclient.discovery import build
        creds_json = get_indexing_credentials()
        if not creds_json:
            return jsonify({'success': False, 'error': 'Google credentials not configured'}), 400
        base_url = request.host_url.rstrip('/').replace('http://', 'https://')
        urls = [
            f"{base_url}/",
            f"{base_url}/chart",
            f"{base_url}/daily-update",
            f"{base_url}/latest",
        ]
        try:
            games = get_all_games_list()
            for game in games:
                slug = create_slug(game)
                urls.append(f"{base_url}/chart?game={slug}")
        except:
            pass
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT slug FROM daily_posts WHERE is_published = true ORDER BY post_date DESC LIMIT 500")
            posts = cur.fetchall()
            cur.close()
            conn.close()
            for post in posts:
                urls.append(f"{base_url}/{post[0]}")
        except:
            pass
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT slug FROM manual_posts WHERE is_published = true")
            posts = cur.fetchall()
            cur.close()
            conn.close()
            for post in posts:
                urls.append(f"{base_url}/{post[0]}")
        except:
            pass
        SCOPES = ['https://www.googleapis.com/auth/indexing']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scopes=SCOPES)
        service = build('indexing', 'v3', credentials=credentials)
        results = []
        for url in urls:
            try:
                result = service.urlNotifications().publish(body={'url': url, 'type': 'URL_UPDATED'}).execute()
                results.append({'url': url, 'status': 'success', 'response': str(result)})
            except Exception as e:
                results.append({'url': url, 'status': 'error', 'error': str(e)})
        return jsonify({'success': True, 'results': results, 'total_urls': len(urls)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/robots.txt')
def robots_txt():
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    content = f"""User-agent: *
Allow: /
Allow: /chart
Allow: /daily-update
Allow: /latest
Allow: /privacy-policy
Allow: /about
Allow: /contact
Allow: /disclaimer
Allow: /robots.txt
Allow: /ads.txt
Allow: /sitemap.xml
Allow: /sitemap-*.xml

Disallow: /admin
Disallow: /admin/
Disallow: /api/
Disallow: /download-project
Disallow: /*.py$
Disallow: /*.py.backup$
Disallow: /*.md$
Disallow: /*.toml$
Disallow: /*.lock$
Disallow: /*.sh$
Disallow: /*.env$
Disallow: /venv/
Disallow: /.git/
Disallow: /.cache/
Disallow: /.local/
Disallow: /.streamlit/
Disallow: /.pythonlibs/
Disallow: /.upm/
Disallow: /attached_assets/
Disallow: /templates/
Disallow: /*?o=
Disallow: /*&o=

Sitemap: {base_url}/sitemap.xml
"""
    return content, 200, {'Content-Type': 'text/plain'}

@app.route('/ads.txt')
def ads_txt():
    ad_settings = get_ad_settings()
    ads_content = ad_settings.get('ads_txt_content', '')
    if not ads_content:
        ads_content = "# No ads.txt content configured yet\n# Add your AdSense ads.txt content in Admin Panel > Ads Management"
    return ads_content, 200, {'Content-Type': 'text/plain'}

@app.route('/sitemap.xml')
def sitemap_index():
    now = get_ist_now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>{base_url}/sitemap-pages.xml</loc>
        <lastmod>{now}</lastmod>
    </sitemap>
    <sitemap>
        <loc>{base_url}/sitemap-daily.xml</loc>
        <lastmod>{now}</lastmod>
    </sitemap>
    <sitemap>
        <loc>{base_url}/sitemap-charts.xml</loc>
        <lastmod>{now}</lastmod>
    </sitemap>
    <sitemap>
        <loc>{base_url}/sitemap-latest.xml</loc>
        <lastmod>{now}</lastmod>
    </sitemap>
</sitemapindex>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/sitemap-pages.xml')
def sitemap_pages():
    now = get_ist_now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{now}</lastmod>
        <changefreq>hourly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{base_url}/chart</loc>
        <lastmod>{now}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>{base_url}/daily-update</loc>
        <lastmod>{now}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>{base_url}/latest</loc>
        <lastmod>{now}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/sitemap-daily.xml')
def sitemap_daily():
    now = get_ist_now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    urls = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT slug, updated_at FROM daily_posts WHERE is_published = true ORDER BY post_date DESC LIMIT 50000")
        posts = cur.fetchall()
        cur.close()
        conn.close()
        for post in posts:
            lastmod = post[1].strftime('%Y-%m-%dT%H:%M:%S+05:30') if post[1] else now
            urls.append(f'''    <url>
        <loc>{base_url}/{post[0]}</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>''')
    except:
        pass
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/sitemap-charts.xml')
def sitemap_charts():
    now = get_ist_now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    urls = []
    try:
        games = get_all_games_list()
        for game in games:
            slug = create_slug(game)
            urls.append(f'''    <url>
        <loc>{base_url}/chart?game={slug}</loc>
        <lastmod>{now}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>''')
    except:
        pass
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/sitemap-latest.xml')
def sitemap_latest():
    now = get_ist_now().strftime('%Y-%m-%dT%H:%M:%S+05:30')
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    urls = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT slug, updated_at FROM manual_posts WHERE is_published = true ORDER BY created_at DESC LIMIT 50000")
        posts = cur.fetchall()
        cur.close()
        conn.close()
        for post in posts:
            lastmod = post[1].strftime('%Y-%m-%dT%H:%M:%S+05:30') if post[1] else now
            urls.append(f'''    <url>
        <loc>{base_url}/latest/{post[0]}</loc>
        <lastmod>{lastmod}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.7</priority>
    </url>''')
    except:
        pass
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''
    return xml, 200, {'Content-Type': 'application/xml'}

@app.route('/api/sitemap-stats')
def sitemap_stats():
    stats = {'pages': 4, 'daily': 0, 'charts': 0, 'latest': 0, 'total': 4}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_posts WHERE is_published = true")
        stats['daily'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT name) FROM games WHERE is_active = true")
        stats['charts'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM manual_posts WHERE is_published = true")
        stats['latest'] = cur.fetchone()[0]
        cur.close()
        conn.close()
        stats['total'] = stats['pages'] + stats['daily'] + stats['charts'] + stats['latest']
    except:
        pass
    return jsonify(stats)

@app.route('/api/import-stats')
def import_stats():
    stats = {'unique_games': 0, 'total_results': 0, 'date_range': '-'}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(DISTINCT game_name) FROM game_results")
        stats['unique_games'] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM game_results")
        stats['total_results'] = cur.fetchone()[0]
        cur.execute("SELECT MIN(result_date), MAX(result_date) FROM game_results")
        row = cur.fetchone()
        if row[0] and row[1]:
            stats['date_range'] = f"{row[0].strftime('%b %Y')} - {row[1].strftime('%b %Y')}"
        cur.close()
        conn.close()
    except:
        pass
    return jsonify(stats)

GAMES_LIST = [
    {'name': 'GALI', 'slug': 'gl'},
    {'name': 'DESAWAR', 'slug': 'ds'},
    {'name': 'GHAZIABAD', 'slug': 'gb'},
    {'name': 'FARIDABAD', 'slug': 'fb'},
    {'name': 'SHRI GANESH', 'slug': 'sg'},
    {'name': 'DELHI BAZAR', 'slug': 'db'},
    {'name': 'DELHI CITY', 'slug': 'dc'},
    {'name': 'RAM BAZAR', 'slug': 'rb'},
    {'name': 'BIKANER SUPER', 'slug': 'bs'},
    {'name': 'NEW PUNJAB', 'slug': 'np'},
    {'name': 'ROYAL BAZAR', 'slug': 'ro'},
    {'name': 'SURAT CITY', 'slug': 'sc'},
    {'name': 'GURU MANGAL', 'slug': 'gm'},
    {'name': 'SUPER KING', 'slug': 'su'},
    {'name': 'MATKA SONE KA', 'slug': 'mo'},
    {'name': 'U.P KING', 'slug': 'ui'},
    {'name': 'RAJDHANI JAIPUR', 'slug': 'rj'},
    {'name': 'AGRA BAZAR', 'slug': 'az'},
    {'name': 'BIHAR KING', 'slug': 'bk'},
    {'name': 'JANTA CITY', 'slug': 'jc'},
    {'name': 'BURJ KHALIFA - BK', 'slug': 'bj'},
    {'name': 'SHREE GANGA NAGAR', 'slug': 'eg'},
    {'name': 'JAIPUR KING', 'slug': 'jr'},
    {'name': 'MATKA KING', 'slug': 'mt'},
    {'name': 'SUPER TAJ', 'slug': 'st'},
    {'name': 'KALKA BAZAR', 'slug': 'kb'},
    {'name': 'SAVERA', 'slug': 'sv'},
    {'name': 'SUPER DELHI', 'slug': 'sp'},
    {'name': 'DELHI DREAM', 'slug': 'dz'},
    {'name': 'CHENNAI', 'slug': 'cn'},
    {'name': 'MOHALI', 'slug': 'mh'},
    {'name': 'MEERUT CITY', 'slug': 'mc'},
    {'name': 'MANGAL BAZAR', 'slug': 'mr'},
    {'name': 'ROYAL CHALLENGE', 'slug': 'rc'},
    {'name': 'TAJ', 'slug': 'tj'},
    {'name': 'BADLAPUR', 'slug': 'bl'},
    {'name': 'MAA BHAGWATI', 'slug': 'mb'},
    {'name': 'ANARKALI', 'slug': 'ak'},
    {'name': 'DUBAI DELHI', 'slug': 'da'},
    {'name': 'CHAND TARA', 'slug': 'ct'},
    {'name': 'SHIV SHAKTI', 'slug': 'ss'},
    {'name': 'MEWAT', 'slug': 'mw'},
    {'name': 'GHAZIABAD DIN', 'slug': 'gd'},
    {'name': 'AHMEDABAD', 'slug': 'am'},
    {'name': 'HINDUSTAN', 'slug': 'hi'},
    {'name': 'MAHARAJ', 'slug': 'mj'},
    {'name': 'UTTARAKHAND - UK', 'slug': 'uk'},
    {'name': 'RAJDHANI', 'slug': 'ra'},
    {'name': 'DELHI DAY', 'slug': 'dd'},
    {'name': 'GOA KING', 'slug': 'go'},
    {'name': 'OLD CITY', 'slug': 'oc'},
    {'name': 'NEELKANTH', 'slug': 'nl'},
    {'name': 'SUPER MAX', 'slug': 'sx'},
    {'name': 'SHRI LAXMI', 'slug': 'sl'},
    {'name': 'UTTAM NAGAR', 'slug': 'un'},
    {'name': 'DUBAI BAZAR', 'slug': 'di'},
    {'name': 'PARAS', 'slug': 'ps'},
    {'name': 'FARIDA BAZAR', 'slug': 'fr'},
    {'name': 'VEERA', 'slug': 'vr'},
    {'name': 'DELHI GOLDEN', 'slug': 'dg'},
    {'name': 'DELHI STAR', 'slug': 'es'},
    {'name': 'LUCK', 'slug': 'lk'},
    {'name': 'DHAN KUBER', 'slug': 'ku'},
    {'name': 'TODAY BAZAAR', 'slug': 'tb'},
    {'name': 'ROYAL DELHI', 'slug': 'ry'},
    {'name': 'NEW SAHIBABAD', 'slug': 'ns'},
    {'name': 'SAWARIYA SETH', 'slug': 'sw'},
    {'name': 'SHRI JI', 'slug': 'sj'},
    {'name': 'SHIV SHANKAR', 'slug': 'sk'},
    {'name': 'GALI DISAWAR MIX', 'slug': 'gr'},
    {'name': 'WHITE GOLD', 'slug': 'wg'},
    {'name': 'UP BAZAR', 'slug': 'ub'},
    {'name': 'PATHANKOT', 'slug': 'pk'},
    {'name': 'BOMBAY SUPER', 'slug': 'bo'},
    {'name': 'NEW DELHI DARBAR', 'slug': 'br'},
    {'name': 'GHAZIABAD NIGHT', 'slug': 'gz'},
    {'name': 'NEW HYDERABAD', 'slug': 'nh'},
    {'name': 'ROZANA', 'slug': 'rz'},
    {'name': 'BRIJ RANI', 'slug': 'bi'},
    {'name': 'SHRI VISHNU', 'slug': 'vs'},
    {'name': 'MUMBAI STAR', 'slug': 'mm'},
    {'name': 'NEW GHAZIABAD', 'slug': 'ng'},
    {'name': 'BALA JI DADRI', 'slug': 'bd'},
    {'name': 'JAISALMER', 'slug': 'jm'},
    {'name': 'CHOTI GALI', 'slug': 'cg'},
    {'name': 'NEW GALI', 'slug': 'nw'},
    {'name': 'DELHI EVENING', 'slug': 'de'},
]

@app.route('/api/import-games-list')
def import_games_list():
    return jsonify({'games': GAMES_LIST, 'total': len(GAMES_LIST)})

@app.route('/api/import-historical', methods=['POST'])
def import_historical():
    try:
        data = request.get_json() or {}
        start_year = data.get('start_year', 2024)
        start_month = data.get('start_month', 1)
        game_index = data.get('game_index', 0)
        
        if game_index >= len(GAMES_LIST):
            return jsonify({'success': True, 'done': True, 'message': 'All games imported'})
        
        game = GAMES_LIST[game_index]
        now = get_ist_now()
        end_year = now.year
        end_month = now.month
        
        total_imported = 0
        skipped = 0
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        
        year = start_year
        month = start_month
        
        while year < end_year or (year == end_year and month <= end_month):
            try:
                game_slug = game['name'].lower().replace(' ', '-').replace('.', '').replace('- ', '')
                url = f"https://satta-king-fast.com/{game_slug}/satta-result-chart/{game['slug']}/?month={month:02d}&year={year}"
                
                response = scraper.get(url, timeout=15)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                first_cell = cells[0].get_text(strip=True)
                                if first_cell.isdigit():
                                    day = int(first_cell)
                                    if 1 <= day <= 31:
                                        result = cells[-1].get_text(strip=True)
                                        if result and result != 'XX' and result != '--' and len(result) <= 3 and result.isdigit():
                                            try:
                                                result_date = f"{year}-{month:02d}-{day:02d}"
                                                cur.execute("""
                                                    INSERT INTO game_results (game_name, result_date, result)
                                                    VALUES (%s, %s, %s)
                                                    ON CONFLICT (game_name, result_date) DO NOTHING
                                                """, (game['name'], result_date, result))
                                                if cur.rowcount > 0:
                                                    total_imported += 1
                                                else:
                                                    skipped += 1
                                            except:
                                                skipped += 1
            except:
                pass
            
            month += 1
            if month > 12:
                month = 1
                year += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'done': False,
            'game_name': game['name'],
            'game_index': game_index,
            'total_games': len(GAMES_LIST),
            'imported': total_imported,
            'skipped': skipped
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/favicon.ico')
def favicon():
    settings = get_site_settings()
    if settings.get('favicon_data'):
        import io
        favicon_data = settings['favicon_data']
        if ',' in favicon_data:
            favicon_data = favicon_data.split(',')[1]
        image_data = base64.b64decode(favicon_data)
        return image_data, 200, {'Content-Type': 'image/x-icon'}
    return '', 404

@app.route('/api/redirect-settings', methods=['GET'])
def api_get_redirect_settings():
    settings = get_site_settings()
    return jsonify({
        'redirect_404_enabled': settings.get('redirect_404_enabled', True),
        'redirect_404_url': settings.get('redirect_404_url', '/')
    })

@app.route('/api/redirect-settings', methods=['POST'])
def api_save_redirect_settings():
    try:
        data = request.json
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM site_settings LIMIT 1")
        existing = cur.fetchone()
        
        if existing:
            cur.execute("""UPDATE site_settings SET 
                redirect_404_enabled = %s, redirect_404_url = %s, updated_at = %s 
                WHERE id = %s""",
                (data.get('redirect_404_enabled', True), 
                 data.get('redirect_404_url', '/'),
                 get_ist_now(), existing[0]))
        else:
            cur.execute("""INSERT INTO site_settings (redirect_404_enabled, redirect_404_url, updated_at)
                VALUES (%s, %s, %s)""",
                (data.get('redirect_404_enabled', True), 
                 data.get('redirect_404_url', '/'),
                 get_ist_now()))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Redirect settings saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def page_not_found(e):
    if request.path.endswith(('.py', '.py.backup', '.md', '.toml', '.lock', '.gz', '.sh', '.cfg', '.ini', '.log')):
        return '', 410
    
    old_paths = ['/category/', '/post/samsung', '/post/nokia', '/post/realme', '/post/vivo', 
                 '/post/oppo', '/post/xiaomi', '/post/iphone', '/post/oneplus', '/post/motorola',
                 '/post/redmi', '/post/poco', '/post/tecno', '/post/infinix', '/post/iqoo',
                 '/post/nothing', '/post/google-pixel', '/post/honor', '/post/lava', '/post/micromax']
    for old_path in old_paths:
        if request.path.startswith(old_path):
            return '', 410
    
    return "Page Not Found", 404

@app.route('/download-project')
def download_project():
    import subprocess
    import os
    
    project_path = '/home/runner/workspace'
    tar_file = os.path.join(project_path, 'sattaking-project.tar.gz')
    
    subprocess.run(['tar', '-czvf', tar_file, 'main.py', 'templates/', 'pyproject.toml'], 
                   cwd=project_path, capture_output=True)
    
    return send_file(tar_file, as_attachment=True, download_name='sattaking-project.tar.gz')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
