FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl

RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

RUN wget -O /tmp/udp2raw.tar.gz "https://github.com/wangyu-/udp2raw/releases/download/20230206.0/udp2raw_binaries.tar.gz" \
    && mkdir -p /tmp/udp2raw \
    && tar -xzf /tmp/udp2raw.tar.gz -C /tmp/udp2raw \
    && cp /tmp/udp2raw/udp2raw_amd64 /usr/local/bin/udp2raw \
    && chmod +x /usr/local/bin/udp2raw \
    && rm -rf /tmp/udp2raw*

RUN mkdir -p /var/log/supervisor /etc/hysteria

RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem -out /etc/hysteria/cert.pem -days 365 -nodes -subj "/CN=attomic-production.up.railway.app"

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
