FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    dnsutils \
    nginx \
    libnginx-mod-stream \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# نصب dnscrypt-proxy
RUN wget https://github.com/DNSCrypt/dnscrypt-proxy/releases/download/2.1.5/dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz \
    && tar -xzf dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz \
    && cp linux-x86_64/dnscrypt-proxy /usr/sbin/ \
    && chmod +x /usr/sbin/dnscrypt-proxy \
    && rm -rf dnscrypt-proxy-linux_x86_64-2.1.5.tar.gz linux-x86_64

# نصب danted (SOCKS5 proxy)
RUN apt-get update && apt-get install -y dante-server || true

# نصب lightway-proxy (Python)
RUN pip3 install aiohttp

RUN mkdir -p /var/log/supervisor /run/nginx /etc/dnscrypt-proxy /etc/danted

COPY dnscrypt-proxy.toml /etc/dnscrypt-proxy/dnscrypt-proxy.toml
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY lightway-proxy.py /lightway-proxy.py
COPY danted.conf /etc/danted.conf

RUN chmod +x /lightway-proxy.py

EXPOSE 80 443 1080

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
