FROM alpine:latest

RUN apk add --no-cache \
    curl \
    supervisor \
    nginx \
    ca-certificates \
    tar \
    xz \
    libstdc++ \
    jq

RUN curl -sL "https://api.github.com/repos/klzgrad/naiveproxy/releases/latest" | jq -r '.assets[] | select(.name | endswith("linux-x64.tar.xz")) | .browser_download_url' | xargs curl -L -o /tmp/naive.tar.xz \
    && ls -la /tmp/naive.tar.xz \
    && file /tmp/naive.tar.xz || true \
    && tar -xJf /tmp/naive.tar.xz -C /tmp \
    && ls -la /tmp/ \
    && find /tmp -name "naive" -type f -exec cp {} /usr/local/bin/naive \; \
    && chmod +x /usr/local/bin/naive \
    && ls -la /usr/local/bin/naive \
    && rm -rf /tmp/naive*

RUN mkdir -p /var/log/supervisor /run/nginx

COPY config.json /etc/naive/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
