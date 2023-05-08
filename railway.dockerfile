FROM python:3.11-alpine as base

FROM base as builder

RUN apk update && apk upgrade
RUN apk add --no-cache git g++ musl-dev libffi-dev openssl-dev
RUN pip install --upgrade pip

WORKDIR /install
COPY ./xieffect/requirements.txt /requirements.txt
RUN pip install --prefix=/install -r /requirements.txt

FROM alpine/git as copier

COPY ./xieffect /xieffect

ARG RAILWAY_GIT_COMMIT_SHA

WORKDIR /project
RUN git clone https://github.com/xi-effect/xi.backend.git .
RUN git checkout $RAILWAY_GIT_COMMIT_SHA
RUN git submodule init
RUN git submodule update

FROM base

COPY --from=builder /install /usr/local
RUN apk --no-cache add libpq

WORKDIR /backend
COPY --from=copier /project/static static
COPY --from=copier /project/xieffect xieffect
COPY --from=copier /project/*.sh xieffect
RUN chmod +x xieffect/*.sh

WORKDIR /backend/xieffect
EXPOSE 5000

ENTRYPOINT ["./gunicorn.sh"]
