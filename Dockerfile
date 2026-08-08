FROM alpine:latest

RUN apk add --no-cache \
    curl \
    supervisor \
    nginx \
    ca-certificates \
    tar \
    xz \
    libstdc++

# دانلود و نصب NaiveProxy - نسخه دقیق
RUN curl -L "https://github.com/klzgrad/naiveproxy/releases/download/v130.0.6723.58-1/naiveproxy-v130.0.6723.58-1-linux-x64.tar.xz" -o /tmp/naive.tar.xz \
    && tar -xJf /tmp/naive.tar.xz -C /tmp \
    && ls -la /tmp/naiveproxy-* \
    && cp /tmp/naiveproxy-*/naive /usr/local/bin/naive \
    && chmod +x /usr/local/bin/naive \
    && ls -la /usr/local/bin/naive \
    && /usr/local/bin/naive --version \
    && rm -rf /tmp/naive*

RUN mkdir -p /var/log/supervisor /run/nginx

COPY config.json /etc/naive/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
