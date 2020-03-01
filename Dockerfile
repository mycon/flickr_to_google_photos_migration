FROM "python:3.8-buster"

RUN mkdir -p /app
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app
