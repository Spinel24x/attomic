FROM alpine:latest

RUN apk add --no-cache \
    supervisor \
    nginx \
    curl

RUN mkdir -p /var/log/supervisor /run/nginx /etc/nginx/http.d

RUN echo 'server { listen 443; location / { proxy_pass http://1.1.1.1; proxy_http_version 1.1; proxy_set_header Host $host; } }' > /etc/nginx/http.d/default.conf

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
