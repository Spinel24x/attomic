FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    dnsutils \
    nginx-full \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/DNSCrypt/dnscrypt-proxy/releases/download/2.1.5/dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz \
    && tar -xzf dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz \
    && cp linux-x86_64/dnscrypt-proxy /usr/sbin/ \
    && chmod +x /usr/sbin/dnscrypt-proxy \
    && rm -rf dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz linux-x86_64

RUN mkdir -p /var/log/supervisor /run/nginx /etc/dnscrypt-proxy

COPY dnscrypt-proxy.toml /etc/dnscrypt-proxy/dnscrypt-proxy.toml
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
