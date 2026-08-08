FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    ca-certificates \
    openssl \
    iptables \
    iproute2

# Hysteria2 آخرین نسخه
RUN wget -O /usr/local/bin/hysteria "https://github.com/apernet/hysteria/releases/latest/download/hysteria-linux-amd64" \
    && chmod +x /usr/local/bin/hysteria \
    && echo "Hysteria version:" && /usr/local/bin/hysteria version

# بهینه‌سازی سیستم
RUN echo "net.core.rmem_max=25000000" >> /etc/sysctl.conf \
    && echo "net.core.wmem_max=25000000" >> /etc/sysctl.conf \
    && echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf \
    && echo "net.ipv4.tcp_notsent_lowat=16384" >> /etc/sysctl.conf

RUN mkdir -p /var/log/supervisor /etc/hysteria

# ساخت گواهی
RUN openssl req -x509 -newkey rsa:4096 -keyout /etc/hysteria/key.pem \
    -out /etc/hysteria/cert.pem -days 3650 -nodes \
    -subj "/C=US/ST=CA/L=SanFrancisco/O=Cloudflare/OU=CDN/CN=attomic-production.up.railway.app" \
    -addext "subjectAltName=DNS:attomic-production.up.railway.app,DNS:*.up.railway.app"

# اسکریپت startup
RUN echo '#!/bin/sh' > /start.sh \
    && echo 'sysctl -p || true' >> /start.sh \
    && echo 'iptables -A INPUT -p tcp --dport 443 -j ACCEPT || true' >> /start.sh \
    && echo 'iptables -A INPUT -p udp --dport 443 -j ACCEPT || true' >> /start.sh \
    && echo 'ulimit -n 1048576' >> /start.sh \
    && chmod +x /start.sh

COPY config.yaml /etc/hysteria/config.yaml
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443/udp 443/tcp

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
