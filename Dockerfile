FROM python:3

ENV IS_DOCKER True

WORKDIR /usr/src/sungather

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY SunGather/ .
RUN touch /config/config.yaml

CMD [ "python", "sungather.py" ]