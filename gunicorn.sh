#!/bin/sh
sleep 1
gunicorn \
  --bind 0.0.0.0:5000 \
  -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
  --workers 1 \
  --timeout 600 \
  --log-level 'debug' \
  wsgi:application
