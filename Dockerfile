FROM alpine:latest

RUN apk add --no-cache \
    curl \
    wget \
    supervisor \
    tor \
    obfs4proxy \
    ca-certificates

RUN mkdir -p /var/log/supervisor /etc/tor

RUN echo 'SOCKSPort 0' > /etc/tor/torrc \
    && echo 'ORPort 443' >> /etc/tor/torrc \
    && echo 'BridgeRelay 1' >> /etc/tor/torrc \
    && echo 'ExitRelay 0' >> /etc/tor/torrc \
    && echo 'ServerTransportPlugin obfs4 exec /usr/bin/obfs4proxy' >> /etc/tor/torrc \
    && echo 'ExtORPort auto' >> /etc/tor/torrc \
    && echo 'Nickname attomic' >> /etc/tor/torrc

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 443

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
