FROM python:3.11-alpine as base

FROM base as builder

RUN apk update && apk upgrade
RUN apk add --no-cache git g++ musl-dev libffi-dev openssl-dev
RUN pip install --upgrade pip

WORKDIR /install
COPY ./xieffect/requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

FROM base

COPY --from=builder /install /usr/local
RUN apk --no-cache add libpq

WORKDIR /backend
COPY ./static static
COPY ./xieffect xieffect

WORKDIR /backend/xieffect
EXPOSE 5000

ENTRYPOINT gunicorn \
    --bind 0.0.0.0:5000 \
    -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
    --workers 1 \
    --timeout 600 \
    wsgi:application
