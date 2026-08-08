FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates

# دانلود Hysteria2
RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

RUN mkdir -p /var/log/supervisor /etc/hysteria

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
