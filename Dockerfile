FROM python:3 as builder

RUN python3 -m venv /opt/virtualenv \
 && apt-get update \
 && apt-get install build-essential

COPY requirements.txt ./
# pycryptodomex 3.14 currently fails to compile for arm64
RUN /opt/virtualenv/bin/pip3 install --no-cache-dir --upgrade pycryptodomex==3.11.0 -r requirements.txt

FROM python:3-slim

RUN useradd -r -m sungather

COPY --from=builder /opt/virtualenv /opt/virtualenv

WORKDIR /opt/sungather

COPY SunGather/ .

VOLUME /logs
VOLUME /config
COPY SunGather/config-example.yaml /config/config.yaml

USER sungather

CMD [ "/opt/virtualenv/bin/python", "sungather.py", "-c", "/config/config.yaml", "-l", "/logs/" ]
