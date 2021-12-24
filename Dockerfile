FROM python:3-slim

RUN useradd sungather

WORKDIR /usr/src/sungather

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY SunGather/ .

VOLUME /config
COPY SunGather/config-example.yaml /config/config.yaml

USER sungather

CMD [ "python", "sungather.py", "-c", "/config/config.yaml" ]