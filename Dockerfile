FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/i2p/i2p.i2p/releases/download/i2p-2.4.0/i2pinstall_2.4.0.jar \
    && java -jar i2pinstall_2.4.0.jar -console \
    && rm i2pinstall_2.4.0.jar

RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 4444 4445 7657

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
