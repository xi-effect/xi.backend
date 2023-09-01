#!/bin/sh
alembic upgrade head
./gunicorn.sh
