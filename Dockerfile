FROM python:3

WORKDIR /usr/src/sungather

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY SunGather/ .
RUN touch /usr/src/sungather/config.yaml

CMD [ "python", "sungather.py" ]