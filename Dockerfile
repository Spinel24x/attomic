FROM alpine:latest

RUN apk add --no-cache \
    dante-server \
    supervisor \
    curl

RUN mkdir -p /var/log/supervisor

COPY danted.conf /etc/danted.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 1080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
