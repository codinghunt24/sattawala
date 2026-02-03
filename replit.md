# Satta King - Replit Configuration

## Overview

This is a Satta King results display application built with Flask (converted from Streamlit for proper SEO). The application provides a public-facing interface for displaying game results and an admin panel for managing games. It uses server-side rendered HTML for full Google indexing compatibility.

## Admin Panel

Access the admin panel at `/admin`. Features include:
- **Game Management**: Add, edit, delete games with name, game time, yesterday/today results, display order
- **Web Scraping**: Fetch games automatically from satta-king-fast.com with Cloudflare bypass
- **Bulk Actions**: Clear all games, refresh data

## Database Schema

### Games Table
- id (SERIAL PRIMARY KEY)
- name (VARCHAR 255)
- game_time (VARCHAR 50)
- yesterday_result (VARCHAR 50)
- today_result (VARCHAR 50)
- is_active (BOOLEAN)
- display_order (INTEGER)
- created_at, updated_at (TIMESTAMP)

### Posts Table
- id (SERIAL PRIMARY KEY)
- title (VARCHAR 255)
- content (TEXT)
- is_published (BOOLEAN)
- created_at, updated_at (TIMESTAMP)

### Game Results Table (for Record Charts)
- id (SERIAL PRIMARY KEY)
- game_name (VARCHAR 255)
- result_date (DATE)
- result (VARCHAR 10)
- created_at (TIMESTAMP)
- UNIQUE(game_name, result_date)

### Scrape Settings Table
- id (SERIAL PRIMARY KEY)
- scrape_url (VARCHAR 500)
- auto_scrape (BOOLEAN)
- interval_minutes (INTEGER)
- last_scrape (TIMESTAMP)

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Flask with Jinja2 templates - chosen for server-side rendering to enable proper SEO
- **Page Structure**:
  - `/` - Homepage showing all active games with results
  - `/chart` - Record chart page with month/year/game filters
  - `/admin` - Administrative interface for content management
- **Styling**: Custom CSS with dark gradient theme, responsive design
- **Templates**: Located in `templates/` folder (base.html, index.html, chart.html, admin.html)

### Backend Architecture
- **Pattern**: Monolithic single-process Flask application
- **Server**: Gunicorn WSGI server (production-ready)
- **Database Access**: Direct PostgreSQL connections using psycopg2
- **Web Scraping**: requests + BeautifulSoup with Cloudflare bypass headers

### Data Storage
- **Database**: PostgreSQL accessed via `DATABASE_URL` environment variable
- **Schema**: 4 tables - games, posts, game_results, scrape_settings
- **Initialization**: Database tables are auto-created on app startup

### Key Design Decisions
1. **Flask over Streamlit**: Chosen for server-side HTML rendering to enable proper SEO (meta tags in HTML `<head>`)
2. **Gunicorn**: Production WSGI server for better performance and reliability
3. **Direct SQL over ORM**: Uses raw psycopg2 queries for minimal dependencies
4. **Environment-based Configuration**: Database URL and secrets stored in environment variables

## External Dependencies

### Database
- **PostgreSQL**: Primary data store, connection string provided via `DATABASE_URL` environment variable

### Python Packages
- **flask**: Web framework
- **gunicorn**: WSGI HTTP server
- **psycopg2**: PostgreSQL database adapter
- **requests**: HTTP client for web scraping
- **beautifulsoup4**: HTML parsing for web scraping

### Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string (required)
- `SESSION_SECRET`: Flask session secret key (optional, has default)

## SEO Implementation

### Why Flask Instead of Streamlit
Streamlit renders content client-side using JavaScript. This means:
- Meta tags are inserted by JavaScript AFTER page load
- Google's crawler may not see the meta tags in the HTML source
- Server-side rendering (Flask) ensures all SEO elements are in the initial HTML response

### URL Structure (SEO-Friendly Slugs)
- Homepage: `/`
- Chart Page: `/chart?game={game-slug}`
- Admin Page: `/admin`
- Example: `/chart?game=gali-disawar-mix` (instead of `GALI%20DISAWAR%20MIX`)

### Monthly Title Format for Google Indexing

Each game's chart page is optimized for search engines with dynamic titles:

**Title Format:**
```
{GAME NAME} Result Chart {Month} {Year} | Satta King Live
```

**Example Titles by Month (for GALI DISAWAR MIX):**

| Month | Year | SEO Title |
|-------|------|-----------|
| January | 2026 | GALI DISAWAR MIX Result Chart January 2026 \| Satta King Live |
| February | 2026 | GALI DISAWAR MIX Result Chart February 2026 \| Satta King Live |
| March | 2026 | GALI DISAWAR MIX Result Chart March 2026 \| Satta King Live |
| April | 2026 | GALI DISAWAR MIX Result Chart April 2026 \| Satta King Live |
| May | 2026 | GALI DISAWAR MIX Result Chart May 2026 \| Satta King Live |
| June | 2026 | GALI DISAWAR MIX Result Chart June 2026 \| Satta King Live |
| July | 2026 | GALI DISAWAR MIX Result Chart July 2026 \| Satta King Live |
| August | 2026 | GALI DISAWAR MIX Result Chart August 2026 \| Satta King Live |
| September | 2026 | GALI DISAWAR MIX Result Chart September 2026 \| Satta King Live |
| October | 2026 | GALI DISAWAR MIX Result Chart October 2026 \| Satta King Live |
| November | 2026 | GALI DISAWAR MIX Result Chart November 2026 \| Satta King Live |
| December | 2026 | GALI DISAWAR MIX Result Chart December 2026 \| Satta King Live |

### SEO Elements Implemented (Server-Side Rendered)

1. **Dynamic Title Tags** - Game name + Month + Year in HTML `<head>`
2. **Meta Description** - Detailed description with target keywords
3. **Meta Keywords** - Game name variations and related terms
4. **Canonical URLs** - Prevents duplicate content issues
5. **Open Graph Tags** - For Facebook/social sharing
6. **Twitter Cards** - For Twitter sharing
7. **Schema.org JSON-LD** - Structured data for rich snippets:
   - WebPage schema
   - Dataset schema (for result data)
   - BreadcrumbList schema (navigation path)

### Target Keywords Per Game
For each game, the following keyword patterns are targeted:
- `{game name}`
- `{game name} result`
- `{game name} chart`
- `{game name} {month} {year}`
- `satta king {game name}`
- `{game name} record`
- `{game name} live result`

## API Routes

### Game Management
- `GET /api/games` - List all games
- `POST /api/games` - Add new game
- `PUT /api/games/<id>` - Update game
- `DELETE /api/games/<id>` - Delete game

### Data Operations
- `POST /api/scrape` - Scrape games from satta-king-fast.com
- `POST /api/clear-games` - Delete all games

## File Structure

```
├── app.py              # Launcher script (starts Gunicorn)
├── main.py             # Flask application with all routes
├── templates/
│   ├── base.html       # Base template with common styles
│   ├── index.html      # Homepage template
│   ├── chart.html      # Record chart template with full SEO
│   └── admin.html      # Admin panel template
├── replit.md           # This file
└── pyproject.toml      # Python dependencies
```
