#!/bin/sh
alembic upgrade head
gunicorn --bind 0.0.0.0:5000 --worker-class eventlet -w 1 wsgi:application
