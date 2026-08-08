FROM alpine:latest

RUN apk add --no-cache \
    dante-server \
    nginx \
    supervisor \
    curl \
    iproute2 \
    python3 \
    py3-pip

RUN pip3 install websockify --break-system-packages

RUN mkdir -p /var/log/supervisor /run/nginx

COPY danted.conf /etc/danted.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80 1080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
