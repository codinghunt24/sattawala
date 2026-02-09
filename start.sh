#!/bin/bash
exec gunicorn -b 0.0.0.0:5000 --workers 2 --timeout 120 main:app
