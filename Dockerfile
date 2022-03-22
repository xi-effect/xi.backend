FROM python:3.9-alpine

RUN apk update && apk upgrade
RUN apk add --no-cache git gcc musl-dev libffi-dev openssl-dev

RUN pip install --upgrade pip
COPY ./__lib__ /app/__lib__
COPY requirements.txt /app
RUN pip3 install -r /app/requirements.txt

COPY ./files /files
COPY ./xieffect /app
COPY ./gunicorn.sh /app/gunicorn.sh
WORKDIR /app

EXPOSE 5000

ENTRYPOINT ["./gunicorn.sh"]
