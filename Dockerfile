FROM alpine:latest

RUN apk add --no-cache \
    curl \
    supervisor \
    nginx \
    libsodium \
    ca-certificates \
    xz

# دانلود نسخه دقیق NaiveProxy
RUN NAIVE_VERSION="127.0.6533.99" \
    && curl -L "https://github.com/klzgrad/naiveproxy/releases/download/v${NAIVE_VERSION}/naiveproxy-v${NAIVE_VERSION}-linux-x64.tar.xz" -o /tmp/naive.tar.xz \
    && ls -la /tmp/naive.tar.xz \
    && file /tmp/naive.tar.xz \
    && tar -xJf /tmp/naive.tar.xz -C /tmp \
    && ls -la /tmp/ \
    && mv /tmp/naiveproxy-*/* /usr/local/bin/ 2>/dev/null || mv /tmp/naiveproxy/* /usr/local/bin/ 2>/dev/null \
    && chmod +x /usr/local/bin/naive \
    && rm -rf /tmp/naive*

RUN mkdir -p /var/log/supervisor /run/nginx /etc/naive

COPY config.json /etc/naive/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
