FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    dante-server \
    nginx \
    supervisor \
    curl \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/log/supervisor /run/nginx

COPY danted.conf /etc/danted.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80 53

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
