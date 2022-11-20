FROM python:3.9-alpine

WORKDIR /backend
RUN apk update && apk upgrade
RUN apk add --no-cache git g++ musl-dev libffi-dev openssl-dev

RUN pip3 install --upgrade pip
COPY ./xieffect/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./static static
COPY ./xieffect xieffect
COPY ./*.sh xieffect
RUN chmod +x xieffect/*.sh

WORKDIR /backend/xieffect
EXPOSE 5000

ENTRYPOINT ["./gunicorn.sh"]
