#!/usr/bin/env python3
import socket
import struct
import select
import sys

def handle(client):
    try:
        client.recv(262)
        client.send(b"\x05\x00")
        data = client.recv(262)
        addr_type = data[3]
        if addr_type == 1:
            addr = socket.inet_ntoa(data[4:8])
            port = struct.unpack('>H', data[8:10])[0]
        elif addr_type == 3:
            l = data[4]
            addr = data[5:5+l].decode()
            port = struct.unpack('>H', data[5+l:7+l])[0]
        else:
            client.close()
            return
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((addr, port))
        client.send(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + struct.pack(">H", 0))
        socks = [client, remote]
        while True:
            r, _, _ = select.select(socks, [], [], 60)
            if not r: break
            for s in r:
                d = s.recv(4096)
                if not d: return
                if s is client: remote.send(d)
                else: client.send(d)
    except: pass
    finally:
        client.close()
        try: remote.close()
        except: pass

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', 443))
s.listen(50)

while True:
    c, a = s.accept()
    if __import__('os').fork() == 0:
        s.close()
        handle(c)
        sys.exit(0)
    c.close()
