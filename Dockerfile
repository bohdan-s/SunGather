FROM python:3.13 AS builder

RUN python3 -m venv /opt/virtualenv && \
    apt update && \
    apt install -y build-essential

COPY requirements.txt ./
RUN /opt/virtualenv/bin/pip3 install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

RUN apt update && apt upgrade -y && \
    apt install -y procps sudo && \
    apt clean autoclean && \
    apt autoremove -y && \
    rm -rf /tmp/* && \
    rm -rf /usr/share/doc/* && \
    rm -rf /usr/share/info/* && \
    rm -rf /var/lib/{apt,cache,dpkg,log}/ && \
    rm -rf /var/tmp/*

RUN groupadd -g 1000 sungather && \
    useradd -u 1000 -g sungather -d /opt/sungather -s /bin/false sungather

RUN echo "sungather ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers && \
    chmod 0440 /etc/sudoers && \
    chmod g+w /etc/passwd

COPY --from=builder /opt/virtualenv /opt/virtualenv

WORKDIR /opt/sungather

COPY SunGather/ .

COPY patch/SungrowClient.py /opt/virtualenv/lib/python3.13/site-packages/SungrowClient/
RUN rm -rf /opt/virtualenv/lib/python3.13/site-packages/SungrowClient/__pycache__

VOLUME /logs
VOLUME /config
COPY SunGather/config-example.yaml /config/config.yaml

USER sungather

CMD [ "/opt/virtualenv/bin/python", "sungather.py", "-c", "/config/config.yaml", "-l", "/logs/" ]
