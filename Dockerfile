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
COPY ./*.sh xieffect
RUN chmod +x xieffect/*.sh

WORKDIR /backend/xieffect
EXPOSE 5000

ENTRYPOINT ["./server.sh"]
