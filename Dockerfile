FROM alpine:latest

RUN apk add --no-cache \
    dnscrypt-proxy \
    nginx \
    supervisor \
    curl \
    bash \
    bind-tools

RUN mkdir -p /var/log/supervisor /var/log/nginx /run/nginx /etc/dnscrypt-proxy

COPY dnscrypt-proxy.toml /etc/dnscrypt-proxy/dnscrypt-proxy.toml
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisord.conf

EXPOSE 53/tcp 53/udp 80 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
