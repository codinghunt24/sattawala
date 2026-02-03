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