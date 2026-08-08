#!/usr/bin/env python3

import os
import socket
import struct
import select
import threading
import logging
import ipaddress

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))

USERNAME = os.environ.get("SOCKS5_USERNAME")
PASSWORD = os.environ.get("SOCKS5_PASSWORD")

BUFFER_SIZE = 64 * 1024
TIMEOUT = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("socks5")


def recv_exact(sock, size):
    data = b""

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            raise ConnectionError("Connection closed")

        data += chunk

    return data


def recv_socks5_string(sock):
    length = recv_exact(sock, 1)[0]
    return recv_exact(sock, length)


def authenticate(client):
    header = recv_exact(client, 2)

    version = header[0]
    method_count = header[1]

    if version != 5:
        raise ConnectionError("Invalid SOCKS version")

    methods = recv_exact(client, method_count)

    auth_required = USERNAME is not None and PASSWORD is not None

    if auth_required:
        if 2 not in methods:
            client.sendall(b"\x05\xff")
            return False

        client.sendall(b"\x05\x02")

        version = recv_exact(client, 1)[0]

        if version != 1:
            return False

        username = recv_socks5_string(client).decode(
            "utf-8",
            errors="ignore"
        )

        password = recv_socks5_string(client).decode(
            "utf-8",
            errors="ignore"
        )

        if username != USERNAME or password != PASSWORD:
            client.sendall(b"\x01\x01")
            return False

        client.sendall(b"\x01\x00")
        return True

    if 0 not in methods:
        client.sendall(b"\x05\xff")
        return False

    client.sendall(b"\x05\x00")

    return True


def parse_request(client):
    header = recv_exact(client, 4)

    version = header[0]
    command = header[1]
    reserved = header[2]
    address_type = header[3]

    if version != 5:
        raise ConnectionError("Invalid SOCKS version")

    if command != 1:
        client.sendall(
            b"\x05\x07\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )
        raise ConnectionError("Only CONNECT is supported")

    if address_type == 1:
        raw_addr = recv_exact(client, 4)
        address = socket.inet_ntoa(raw_addr)

    elif address_type == 3:
        length = recv_exact(client, 1)[0]
        raw_addr = recv_exact(client, length)
        address = raw_addr.decode("idna")

    elif address_type == 4:
        raw_addr = recv_exact(client, 16)
        address = socket.inet_ntop(socket.AF_INET6, raw_addr)

    else:
        client.sendall(
            b"\x05\x08\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )
        raise ConnectionError("Unsupported address type")

    raw_port = recv_exact(client, 2)
    port = struct.unpack(">H", raw_port)[0]

    return address, port


def create_remote(address, port):
    last_error = None

    try:
        addr_info = socket.getaddrinfo(
            address,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise ConnectionError(f"DNS resolution failed: {exc}")

    for family, socktype, proto, _, sockaddr in addr_info:
        remote = socket.socket(family, socktype, proto)
        remote.settimeout(TIMEOUT)

        try:
            remote.connect(sockaddr)
            remote.settimeout(None)
            return remote

        except Exception as exc:
            last_error = exc
            remote.close()

    raise ConnectionError(
        f"Could not connect to destination: {last_error}"
    )


def send_success(client, remote):
    try:
        local = remote.getsockname()

        if len(local) >= 2:
            bind_address = local[0]
            bind_port = local[1]
        else:
            bind_address = "0.0.0.0"
            bind_port = 0

        ip = ipaddress.ip_address(bind_address)

        if ip.version == 6:
            response = (
                b"\x05\x00\x00\x04"
                + socket.inet_pton(socket.AF_INET6, bind_address)
                + struct.pack(">H", bind_port)
            )
        else:
            response = (
                b"\x05\x00\x00\x01"
                + socket.inet_aton(bind_address)
                + struct.pack(">H", bind_port)
            )

    except Exception:
        response = (
            b"\x05\x00\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )

    client.sendall(response)


def relay(client, remote):
    sockets = [client, remote]

    while True:
        readable, _, exceptional = select.select(
            sockets,
            [],
            sockets,
            TIMEOUT
        )

        if exceptional:
            break

        if not readable:
            break

        for sock in readable:
            data = sock.recv(BUFFER_SIZE)

            if not data:
                return

            if sock is client:
                remote.sendall(data)
            else:
                client.sendall(data)


def handle_client(client, address):
    remote = None

    try:
        client.settimeout(TIMEOUT)

        logger.info(
            "Client connected: %s:%s",
            address[0],
            address[1]
        )

        if not authenticate(client):
            logger.warning(
                "SOCKS authentication failed: %s:%s",
                address[0],
                address[1]
            )
            return

        destination, port = parse_request(client)

        logger.info(
            "CONNECT %s:%s from %s:%s",
            destination,
            port,
            address[0],
            address[1]
        )

        remote = create_remote(destination, port)

        send_success(client, remote)

        client.settimeout(None)

        relay(client, remote)

    except Exception as exc:
        logger.warning(
            "Connection error from %s:%s: %s",
            address[0],
            address[1],
            exc
        )

    finally:
        try:
            client.close()
        except Exception:
            pass

        if remote:
            try:
                remote.close()
            except Exception:
                pass

        logger.info(
            "Connection closed: %s:%s",
            address[0],
            address[1]
        )


def main():
    server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    try:
        server.setsockopt(
            socket.IPPROTO_IPV6,
            socket.IPV6_V6ONLY,
            0
        )
    except Exception:
        pass

    server.bind(("::", PORT))
    server.listen(256)

    logger.info(
        "SOCKS5 server listening on [::]:%s",
        PORT
    )

    while True:
        client, address = server.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(client, address),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":
    main()
