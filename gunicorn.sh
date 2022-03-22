#!/bin/sh
gunicorn --bind 0.0.0.0:5000 --worker-class eventlet -w 1 wsgi:application
