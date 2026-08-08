FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl \
    iptables

# Hysteria2
RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

# udp2raw
RUN wget -O /usr/local/bin/udp2raw "https://github.com/wangyu-/udp2raw/releases/latest/download/udp2raw_binaries.tar.gz" \
    && tar -xzf /usr/local/bin/udp2raw -C /usr/local/bin/ \
    && mv /usr/local/bin/udp2raw_* /usr/local/bin/udp2raw \
    && chmod +x /usr/local/bin/udp2raw

RUN mkdir -p /var/log/supervisor /etc/hysteria

RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem -out /etc/hysteria/cert.pem -days 365 -nodes -subj "/CN=attomic-production.up.railway.app"

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
