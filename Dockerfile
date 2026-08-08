FROM alpine:edge

RUN apk add --no-cache \
    supervisor \
    nginx \
    naiveproxy \
    curl

RUN mkdir -p /var/log/supervisor /run/nginx /etc/naiveproxy

COPY config.json /etc/naiveproxy/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
