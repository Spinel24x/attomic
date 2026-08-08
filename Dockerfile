FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    openjdk-17-jre-headless \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/i2p/i2p.i2p/releases/download/i2p-2.4.0/i2pinstall_2.4.0.jar \
    && mkdir -p /tmp/i2p \
    && cd /tmp/i2p \
    && /usr/bin/unzip /i2pinstall_2.4.0.jar \
    && ls -la /tmp/i2p/ \
    && mkdir -p /i2p \
    && cp -r /tmp/i2p/* /i2p/ \
    && chmod +x /i2p/i2prouter 2>/dev/null || chmod +x /i2p/installer/lib/i2prouter 2>/dev/null || true \
    && rm /i2pinstall_2.4.0.jar \
    && rm -rf /tmp/i2p

RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 4444 4445 7657

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
