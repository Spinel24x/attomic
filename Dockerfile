FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl

RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

RUN mkdir -p /var/log/supervisor /etc/hysteria

RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem -out /etc/hysteria/cert.pem -days 365 -nodes -subj "/CN=localhost"

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
