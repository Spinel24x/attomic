FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# نصب I2P به صورت headless (بدون GUI)
RUN wget https://github.com/i2p/i2p.i2p/releases/download/i2p-2.4.0/i2pinstall_2.4.0.jar \
    && echo -e "0\n1\n\n\n\n" | java -jar i2pinstall_2.4.0.jar -console \
    && rm i2pinstall_2.4.0.jar

# تنظیمات I2P برای console mode
RUN echo "i2p.dir.base=/i2p" > /i2p/clients.config \
    && echo "i2p.dir.config=/i2p" >> /i2p/clients.config

RUN mkdir -p /var/log/supervisor

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 4444 4445 7657 7070

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
