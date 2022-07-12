FROM python:3.9-alpine

RUN apk update && apk upgrade
RUN apk add --no-cache git gcc musl-dev libffi-dev openssl-dev

RUN pip3 install --upgrade pip
COPY ./xieffect/requirements.txt /app/requirements.txt
COPY ./xieffect/__lib__/requirements.txt /app/__lib__/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY ./static /static
COPY ./xieffect /app
COPY ./*.sh /app
RUN chmod +x /app/*.sh

WORKDIR /app
RUN flask form-sio-docs

EXPOSE 5000

ENTRYPOINT ["/app/gunicorn.sh"]
