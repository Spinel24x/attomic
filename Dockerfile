FROM python:3.11-alpine

RUN apk add --no-cache supervisor nginx

RUN pip3 install websockify --break-system-packages

RUN mkdir -p /var/log/supervisor /run/nginx

COPY socks5.py /socks5.py
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
