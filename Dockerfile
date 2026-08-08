FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    nginx \
    ca-certificates \
    tar \
    xz \
    libstdc++

# لینک مستقیم آخرین نسخه
RUN wget -O /tmp/naive.tar.xz "https://github.com/klzgrad/naiveproxy/releases/download/v131.0.6778.108-1/naiveproxy-v131.0.6778.108-1-linux-x64.tar.xz" \
    && ls -la /tmp/naive.tar.xz \
    && tar -xJf /tmp/naive.tar.xz -C /tmp \
    && ls -la /tmp/naiveproxy-v131.0.6778.108-1-linux-x64/ \
    && cp /tmp/naiveproxy-v131.0.6778.108-1-linux-x64/naive /usr/local/bin/naive \
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
