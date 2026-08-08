FROM alpine:latest

RUN apk add --no-cache \
    dante-server \
    nginx \
    nginx-mod-stream \
    supervisor \
    curl \
    iproute2

RUN mkdir -p /var/log/supervisor /run/nginx

COPY danted.conf /etc/danted.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 1080 12130

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
