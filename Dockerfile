FROM v2fly/v2fly-core:latest

RUN apk add --no-cache supervisor nginx

RUN mkdir -p /var/log/supervisor /run/nginx /etc/v2ray /etc/nginx/http.d

RUN echo '{"inbounds":[{"port":10000,"listen":"127.0.0.1","protocol":"vmess","settings":{"clients":[{"id":"attomic-uuid-2026","alterId":0}]},"streamSettings":{"network":"ws","wsSettings":{"path":"/ws"}}}],"outbounds":[{"protocol":"freedom","settings":{}}]}' > /etc/v2ray/config.json

RUN echo 'server { listen 443; location /ws { proxy_pass http://127.0.0.1:10000; proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade"; } location / { return 200 "OK"; }}' > /etc/nginx/http.d/default.conf

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
