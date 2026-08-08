FROM alpine:latest

RUN apk add --no-cache \
    curl \
    supervisor \
    nginx \
    ca-certificates \
    tar \
    xz

# دانلود آخرین نسخه NaiveProxy
RUN curl -sL "https://api.github.com/repos/klzgrad/naiveproxy/releases/latest" | grep "browser_download_url.*linux-x64.tar.xz" | cut -d '"' -f 4 | xargs curl -L -o /tmp/naive.tar.xz \
    && tar -xJf /tmp/naive.tar.xz -C /tmp \
    && mv /tmp/naiveproxy-*/naive /usr/local/bin/ \
    && chmod +x /usr/local/bin/naive \
    && rm -rf /tmp/naive*

RUN mkdir -p /var/log/supervisor /run/nginx

COPY config.json /etc/naive/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
