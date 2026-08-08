FROM alpine:latest

RUN apk add --no-cache \
    dante-server \
    supervisor \
    curl \
    iproute2

RUN mkdir -p /var/log/supervisor

COPY danted.conf /etc/danted.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 1080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
