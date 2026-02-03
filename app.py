#!/usr/bin/env python3
"""
Flask app for Satta King website with server-side SEO.
Launches gunicorn to serve the Flask application.
"""
import os
import sys

# Start Flask directly using gunicorn (replaces current process)
os.execvp("gunicorn", ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app"])
