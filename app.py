#!/usr/bin/env python3
import os
import sys

os.execvp("gunicorn", ["gunicorn", "-b", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "main:app"])
