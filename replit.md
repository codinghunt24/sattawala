# Satta King - Replit Configuration

## Overview

This is a Satta King results display application built with Streamlit. The application provides a public-facing interface for displaying game results and an admin panel for managing games and posts. It follows a simple monolithic architecture using Python with Streamlit as the web framework and PostgreSQL for data persistence.

## Admin Panel

Access the admin panel from the sidebar in Streamlit. The admin panel has:
- **Game Management**: Add, edit, delete games with name, result, result time, and active status
- **Post Management**: Add, edit, delete posts with title, content, and publish status

## Database Schema

### Games Table
- id (SERIAL PRIMARY KEY)
- name (VARCHAR 255)
- result (VARCHAR 50)
- result_time (VARCHAR 50)
- is_active (BOOLEAN)
- created_at, updated_at (TIMESTAMP)

### Posts Table
- id (SERIAL PRIMARY KEY)
- title (VARCHAR 255)
- content (TEXT)
- is_published (BOOLEAN)
- created_at, updated_at (TIMESTAMP)

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit - chosen for rapid Python-based web development with built-in UI components
- **Page Structure**: Multi-page Streamlit app using the `pages/` directory convention
  - `app.py` - Main public-facing page with custom styling to hide Streamlit's default UI elements
  - `pages/admin.py` - Administrative interface for content management
- **Styling**: Custom CSS injected via `st.markdown()` to create a clean, white-label appearance by hiding Streamlit branding

### Backend Architecture
- **Pattern**: Monolithic single-process application
- **Database Access**: Direct PostgreSQL connections using psycopg2
- **State Management**: Streamlit's `st.session_state` for maintaining user session data

### Data Storage
- **Database**: PostgreSQL accessed via `DATABASE_URL` environment variable
- **Schema**:
  - `games` table: Stores game names, results, result times, and active status
  - `posts` table: Stores content posts with publish status
- **Initialization**: Database tables are auto-created on admin page load if they don't exist

### Key Design Decisions
1. **Streamlit over Flask/Django**: Chosen for simplicity and rapid development of data-focused applications without needing separate frontend code
2. **Direct SQL over ORM**: Uses raw psycopg2 queries rather than an ORM like SQLAlchemy, keeping dependencies minimal
3. **Environment-based Configuration**: Database URL stored in environment variable for security and deployment flexibility

## External Dependencies

### Database
- **PostgreSQL**: Primary data store, connection string provided via `DATABASE_URL` environment variable

### Python Packages
- **streamlit**: Web framework and UI components
- **psycopg2**: PostgreSQL database adapter

### Environment Variables Required
- `DATABASE_URL`: PostgreSQL connection string (required for database functionality)

## SEO Implementation

### URL Structure (SEO-Friendly Slugs)
- Homepage: `/`
- Chart Page: `/chart?game={game-slug}`
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

### SEO Elements Implemented

1. **Dynamic Title Tags** - Game name + Month + Year
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