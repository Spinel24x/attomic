FROM alpine:latest

RUN apk add --no-cache \
    curl \
    supervisor \
    nginx \
    libsodium \
    ca-certificates

# دانلود NaiveProxy
RUN curl -L https://github.com/klzgrad/naiveproxy/releases/latest/download/naiveproxy-v127.0.6533.99-1-linux-x64.tar.xz -o /tmp/naive.tar.xz \
    && tar -xf /tmp/naive.tar.xz -C /tmp \
    && mv /tmp/naiveproxy-*/* /usr/local/bin/ \
    && chmod +x /usr/local/bin/naive \
    && rm -rf /tmp/naive*

RUN mkdir -p /var/log/supervisor /run/nginx

COPY config.json /etc/naive/config.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 80 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
