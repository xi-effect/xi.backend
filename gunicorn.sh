#!/bin/sh
alembic upgrade head
sleep 10
gunicorn --bind 0.0.0.0:5000 --worker-class eventlet --workers 1 wsgi:application --timeout 600 --log-level 'debug'
