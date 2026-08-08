FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl

RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria

RUN mkdir -p /var/log/supervisor /etc/hysteria

RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem -out /etc/hysteria/cert.pem -days 365 -nodes -subj "/CN=localhost"

RUN echo "server: :53" > /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "tls:" >> /etc/hysteria/config.yaml \
    && echo "  cert: /etc/hysteria/cert.pem" >> /etc/hysteria/config.yaml \
    && echo "  key: /etc/hysteria/key.pem" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "auth:" >> /etc/hysteria/config.yaml \
    && echo "  type: password" >> /etc/hysteria/config.yaml \
    && echo "  password: Attomic2026!" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "quic:" >> /etc/hysteria/config.yaml \
    && echo "  initStreamReceiveWindow: 8388608" >> /etc/hysteria/config.yaml \
    && echo "  maxStreamReceiveWindow: 8388608" >> /etc/hysteria/config.yaml \
    && echo "  initConnReceiveWindow: 20971520" >> /etc/hysteria/config.yaml \
    && echo "  maxConnReceiveWindow: 20971520" >> /etc/hysteria/config.yaml \
    && echo "  maxIdleTimeout: 30s" >> /etc/hysteria/config.yaml \
    && echo "  keepAlivePeriod: 10s" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "bandwidth:" >> /etc/hysteria/config.yaml \
    && echo "  up: 500 mbps" >> /etc/hysteria/config.yaml \
    && echo "  down: 500 mbps" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "ignoreClientBandwidth: true" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "speedTest: false" >> /etc/hysteria/config.yaml \
    && echo "" >> /etc/hysteria/config.yaml \
    && echo "disableUDP: false" >> /etc/hysteria/config.yaml \
    && cat /etc/hysteria/config.yaml

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 53

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
