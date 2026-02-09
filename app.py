#!/usr/bin/env python3
import os
import sys

os.execlp(sys.executable, sys.executable, "-m", "gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app")
