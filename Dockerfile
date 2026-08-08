FROM python:3.11-alpine

RUN apk add --no-cache supervisor

RUN mkdir -p /var/log/supervisor

COPY socks5.py /socks5.py
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
