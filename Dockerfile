FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl

# Hysteria2
RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

# GOST (UDP-over-TCP)
RUN wget -O /tmp/gost.tar.gz "https://github.com/ginuerzh/gost/releases/download/v2.11.5/gost-linux-amd64-2.11.5.tar.gz" \
    && tar -xzf /tmp/gost.tar.gz -C /usr/local/bin/ \
    && chmod +x /usr/local/bin/gost \
    && rm /tmp/gost.tar.gz

RUN mkdir -p /var/log/supervisor /etc/hysteria

RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem -out /etc/hysteria/cert.pem -days 365 -nodes -subj "/CN=attomic-production.up.railway.app"

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
