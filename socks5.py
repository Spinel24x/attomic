#!/usr/bin/env python3
import socket
import struct
import select
import sys

def handle_client(client_socket):
    try:
        # SOCKS5 handshake
        client_socket.recv(262)
        client_socket.send(b"\x05\x00")
        
        # Request
        data = client_socket.recv(262)
        mode = data[1]
        addr_type = data[3]
        
        if addr_type == 1:  # IPv4
            addr = socket.inet_ntoa(data[4:8])
            port = struct.unpack('>H', data[8:10])[0]
        elif addr_type == 3:  # Domain
            domain_len = data[4]
            addr = data[5:5+domain_len].decode()
            port = struct.unpack('>H', data[5+domain_len:7+domain_len])[0]
        else:
            client_socket.close()
            return
        
        # Connect to target
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((addr, port))
        
        # Reply success
        reply = b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + struct.pack(">H", 0)
        client_socket.send(reply)
        
        # Tunnel
        sockets = [client_socket, remote]
        while True:
            r, _, _ = select.select(sockets, [], [], 60)
            if not r:
                break
            for s in r:
                data = s.recv(4096)
                if not data:
                    return
                if s is client_socket:
                    remote.send(data)
                else:
                    client_socket.send(data)
    except:
        pass
    finally:
        client_socket.close()
        try:
            remote.close()
        except:
            pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 53))
    server.listen(50)
    print("SOCKS5 Proxy on port 53")
    
    while True:
        client, addr = server.accept()
        print(f"Connection from {addr}")
        pid = __import__('os').fork()
        if pid == 0:
            server.close()
            handle_client(client)
            sys.exit(0)
        client.close()

if __name__ == '__main__':
    main()
