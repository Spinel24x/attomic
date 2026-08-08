#!/usr/bin/env python3

import os
import socket
import struct
import select
import threading
import logging

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

    auth_required = (
        USERNAME is not None and
        PASSWORD is not None
    )

    if auth_required:

        if 2 not in methods:
            client.sendall(b"\x05\xff")
            return False

        client.sendall(b"\x05\x02")

        auth_version = recv_exact(client, 1)[0]

        if auth_version != 1:
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

            logger.warning(
                "SOCKS5 authentication failed"
            )

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
    address_type = header[3]

    if version != 5:
        raise ConnectionError(
            "Invalid SOCKS version"
        )

    if command != 1:

        client.sendall(
            b"\x05\x07\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )

        raise ConnectionError(
            "Only CONNECT command is supported"
        )

    if address_type == 1:

        raw_addr = recv_exact(client, 4)

        address = socket.inet_ntoa(
            raw_addr
        )

    elif address_type == 3:

        length = recv_exact(client, 1)[0]

        raw_addr = recv_exact(
            client,
            length
        )

        address = raw_addr.decode(
            "idna",
            errors="ignore"
        )

    elif address_type == 4:

        # Client requested an IPv6 destination.
        # Railway environment currently has no IPv6
        # outbound route, so reject it cleanly.

        raw_addr = recv_exact(
            client,
            16
        )

        address = socket.inet_ntop(
            socket.AF_INET6,
            raw_addr
        )

        client.sendall(
            b"\x05\x04\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )

        raise ConnectionError(
            f"IPv6 destination is not supported: {address}"
        )

    else:

        client.sendall(
            b"\x05\x08\x00\x01"
            + socket.inet_aton("0.0.0.0")
            + struct.pack(">H", 0)
        )

        raise ConnectionError(
            "Unsupported address type"
        )

    raw_port = recv_exact(
        client,
        2
    )

    port = struct.unpack(
        ">H",
        raw_port
    )[0]

    return address, port


def create_remote(address, port):

    last_error = None

    try:

        # IMPORTANT:
        # AF_INET forces IPv4 DNS resolution.
        #
        # Railway does not currently provide a usable
        # IPv6 outbound route for this service.

        addr_info = socket.getaddrinfo(
            address,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM
        )

    except socket.gaierror as exc:

        raise ConnectionError(
            f"IPv4 DNS resolution failed: {exc}"
        )

    if not addr_info:

        raise ConnectionError(
            f"No IPv4 address found for {address}"
        )

    for family, socktype, proto, _, sockaddr in addr_info:

        remote = socket.socket(
            family,
            socktype,
            proto
        )

        remote.settimeout(
            TIMEOUT
        )

        try:

            remote.connect(
                sockaddr
            )

            remote.settimeout(
                None
            )

            logger.info(
                "Connected to %s:%s via IPv4",
                address,
                port
            )

            return remote

        except Exception as exc:

            last_error = exc

            logger.warning(
                "IPv4 connection failed to %s:%s: %s",
                address,
                port,
                exc
            )

            try:
                remote.close()
            except Exception:
                pass

    raise ConnectionError(
        "Could not connect to destination via IPv4: "
        + str(last_error)
    )


def send_success(client, remote):

    # SOCKS5 CONNECT success reply.
    #
    # We don't need to expose the real remote address.
    # 0.0.0.0:0 is valid for this purpose.

    response = (
        b"\x05\x00\x00\x01"
        + socket.inet_aton("0.0.0.0")
        + struct.pack(">H", 0)
    )

    client.sendall(
        response
    )


def relay(client, remote):

    sockets = [
        client,
        remote
    ]

    while True:

        try:

            readable, _, exceptional = select.select(
                sockets,
                [],
                sockets,
                TIMEOUT
            )

        except Exception as exc:

            logger.warning(
                "Relay select error: %s",
                exc
            )

            break

        if exceptional:
            break

        if not readable:
            logger.info(
                "Relay timeout"
            )

            break

        for sock in readable:

            try:

                data = sock.recv(
                    BUFFER_SIZE
                )

            except Exception as exc:

                logger.warning(
                    "Relay recv error: %s",
                    exc
                )

                return

            if not data:
                return

            try:

                if sock is client:

                    remote.sendall(
                        data
                    )

                else:

                    client.sendall(
                        data
                    )

            except Exception as exc:

                logger.warning(
                    "Relay send error: %s",
                    exc
                )

                return


def handle_client(client, address):

    remote = None

    try:

        client.settimeout(
            TIMEOUT
        )

        logger.info(
            "Client connected: %s:%s",
            address[0],
            address[1]
        )

        if not authenticate(
            client
        ):

            logger.warning(
                "Authentication rejected: %s:%s",
                address[0],
                address[1]
            )

            return

        destination, port = parse_request(
            client
        )

        logger.info(
            "CONNECT %s:%s from %s:%s",
            destination,
            port,
            address[0],
            address[1]
        )

        remote = create_remote(
            destination,
            port
        )

        send_success(
            client,
            remote
        )

        client.settimeout(
            None
        )

        relay(
            client,
            remote
        )

    except ConnectionError as exc:

        logger.warning(
            "Connection error from %s:%s: %s",
            address[0],
            address[1],
            exc
        )

    except Exception as exc:

        logger.exception(
            "Unexpected error from %s:%s: %s",
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

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind(
        (
            HOST,
            PORT
        )
    )

    server.listen(
        256
    )

    logger.info(
        "SOCKS5 server listening on %s:%s",
        HOST,
        PORT
    )

    while True:

        client, address = server.accept()

        logger.info(
            "TCP connection accepted from %s:%s",
            address[0],
            address[1]
        )

        thread = threading.Thread(
            target=handle_client,
            args=(
                client,
                address
            ),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":

    main()
