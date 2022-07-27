FROM python:3-slim

RUN apt-get update && apt-get install -y build-essential python3-dev && rm -rf /var/lib/apt/lists/*

RUN useradd sungather

WORKDIR /usr/src/sungather

COPY requirements.txt ./
# pycryptodomex 3.14 currently fails to compile for arm64
#RUN pip install --no-cache-dir --upgrade -r requirements.txt
RUN pip install --no-cache-dir --upgrade pycryptodomex==3.11.0 -r requirements.txt

COPY SunGather/ .

VOLUME /logs
VOLUME /config
COPY SunGather/config-example.yaml /config/config.yaml

USER sungather

CMD [ "python", "sungather.py", "-c", "/config/config.yaml", "-l", "/logs/" ]