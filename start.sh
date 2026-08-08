#!/bin/sh
IP=$(hostname -i 2>/dev/null || ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d/ -f1)
echo "External IP: $IP"
sed -i "s/__EXTERNAL_IP__/$IP/g" /etc/danted.conf
exec sockd -f /etc/danted.conf
