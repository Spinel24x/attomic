FROM alpine:latest

RUN apk add --no-cache \
    supervisor \
    nginx \
    curl \
    python3

RUN mkdir -p /var/log/supervisor /run/nginx

# SOCKS5 Proxy
COPY socks5.py /socks5.py

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
