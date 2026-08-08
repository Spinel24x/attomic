#!/usr/bin/env python3

import os
import socket
import struct
import select
import threading
import logging


# ============================================================
# Configuration
# ============================================================

HOST = "0.0.0.0"

# Railway provides PORT automatically.
PORT = int(os.environ.get("PORT", "8080"))

# Optional SOCKS5 authentication.
# If these variables are not set, authentication is disabled.
USERNAME = os.environ.get("SOCKS5_USERNAME")
PASSWORD = os.environ.get("SOCKS5_PASSWORD")

BUFFER_SIZE = 64 * 1024

# Connection establishment timeout.
CONNECT_TIMEOUT = 20

# Idle relay timeout.
RELAY_TIMEOUT = 300


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("socks5")


# ============================================================
# SOCKS5 Reply Codes
# ============================================================

REP_SUCCEEDED = 0x00
REP_GENERAL_FAILURE = 0x01
REP_CONNECTION_NOT_ALLOWED = 0x02
REP_NETWORK_UNREACHABLE = 0x03
REP_HOST_UNREACHABLE = 0x04
REP_CONNECTION_REFUSED = 0x05
REP_TTL_EXPIRED = 0x06
REP_COMMAND_NOT_SUPPORTED = 0x07
REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


# ============================================================
# Helper Functions
# ============================================================

def recv_exact(sock, size):
    """
    Receive exactly 'size' bytes.
    """

    data = bytearray()

    while len(data) < size:

        chunk = sock.recv(
            size - len(data)
        )

        if not chunk:
            raise ConnectionError(
                "Connection closed while receiving data"
            )

        data.extend(chunk)

    return bytes(data)


def send_reply(client, reply_code):
    """
    Send a SOCKS5 reply using IPv4 0.0.0.0:0.
    """

    response = (
        b"\x05"
        + bytes([reply_code])
        + b"\x00"
        + b"\x01"
        + socket.inet_aton("0.0.0.0")
        + struct.pack(">H", 0)
    )

    try:
        client.sendall(response)
    except Exception:
        pass


def recv_socks5_string(sock):
    """
    Read SOCKS5 username/password string.
    """

    length = recv_exact(sock, 1)[0]

    if length == 0:
        return b""

    return recv_exact(
        sock,
        length
    )


# ============================================================
# SOCKS5 Authentication
# ============================================================

def authenticate(client):

    header = recv_exact(
        client,
        2
    )

    version = header[0]
    method_count = header[1]

    if version != 5:

        raise ConnectionError(
            "Invalid SOCKS version"
        )

    if method_count == 0:

        client.sendall(
            b"\x05\xff"
        )

        return False

    methods = recv_exact(
        client,
        method_count
    )

    auth_required = (
        USERNAME is not None
        and PASSWORD is not None
    )

    # --------------------------------------------------------
    # Username/password authentication
    # --------------------------------------------------------

    if auth_required:

        if 0x02 not in methods:

            client.sendall(
                b"\x05\xff"
            )

            logger.warning(
                "Client does not support username/password authentication"
            )

            return False

        client.sendall(
            b"\x05\x02"
        )

        auth_version = recv_exact(
            client,
            1
        )[0]

        if auth_version != 1:

            logger.warning(
                "Invalid authentication version"
            )

            return False

        username_raw = recv_socks5_string(
            client
        )

        password_raw = recv_socks5_string(
            client
        )

        username = username_raw.decode(
            "utf-8",
            errors="replace"
        )

        password = password_raw.decode(
            "utf-8",
            errors="replace"
        )

        if (
            username != USERNAME
            or
            password != PASSWORD
        ):

            client.sendall(
                b"\x01\x01"
            )

            logger.warning(
                "SOCKS5 authentication failed"
            )

            return False

        client.sendall(
            b"\x01\x00"
        )

        return True

    # --------------------------------------------------------
    # No authentication
    # --------------------------------------------------------

    if 0x00 not in methods:

        client.sendall(
            b"\x05\xff"
        )

        logger.warning(
            "Client does not support no-authentication"
        )

        return False

    client.sendall(
        b"\x05\x00"
    )

    return True


# ============================================================
# SOCKS5 Request Parser
# ============================================================

def parse_request(client):

    header = recv_exact(
        client,
        4
    )

    version = header[0]
    command = header[1]
    reserved = header[2]
    address_type = header[3]

    if version != 5:

        send_reply(
            client,
            REP_GENERAL_FAILURE
        )

        raise ConnectionError(
            "Invalid SOCKS version"
        )

    # --------------------------------------------------------
    # Only CONNECT is supported
    # --------------------------------------------------------

    if command != 0x01:

        send_reply(
            client,
            REP_COMMAND_NOT_SUPPORTED
        )

        raise ConnectionError(
            f"Unsupported SOCKS5 command: {command}"
        )

    # --------------------------------------------------------
    # IPv4
    # --------------------------------------------------------

    if address_type == 0x01:

        raw_address = recv_exact(
            client,
            4
        )

        address = socket.inet_ntoa(
            raw_address
        )

        address_type_name = "IPv4"

    # --------------------------------------------------------
    # Domain name
    # --------------------------------------------------------

    elif address_type == 0x03:

        domain_length = recv_exact(
            client,
            1
        )[0]

        if domain_length == 0:

            send_reply(
                client,
                REP_GENERAL_FAILURE
            )

            raise ConnectionError(
                "Empty domain name"
            )

        raw_address = recv_exact(
            client,
            domain_length
        )

        # SOCKS5 domain names are transmitted as raw domain
        # name bytes. ASCII is the normal case.
        #
        # errors='replace' is used instead of IDNA with
        # errors='ignore', because Python's IDNA codec does
        # not support the 'ignore' error handler.

        address = raw_address.decode(
            "ascii",
            errors="replace"
        )

        address_type_name = "DOMAIN"

    # --------------------------------------------------------
    # IPv6
    # --------------------------------------------------------

    elif address_type == 0x04:

        raw_address = recv_exact(
            client,
            16
        )

        address = socket.inet_ntop(
            socket.AF_INET6,
            raw_address
        )

        address_type_name = "IPv6"

        # Railway environment currently has no usable IPv6
        # outbound route for this service.

        send_reply(
            client,
            REP_NETWORK_UNREACHABLE
        )

        raise ConnectionError(
            f"IPv6 destination rejected: {address}"
        )

    # --------------------------------------------------------
    # Unsupported address type
    # --------------------------------------------------------

    else:

        send_reply(
            client,
            REP_ADDRESS_TYPE_NOT_SUPPORTED
        )

        raise ConnectionError(
            f"Unsupported address type: {address_type}"
        )

    # --------------------------------------------------------
    # Destination port
    # --------------------------------------------------------

    raw_port = recv_exact(
        client,
        2
    )

    port = struct.unpack(
        ">H",
        raw_port
    )[0]

    if port == 0:

        send_reply(
            client,
            REP_GENERAL_FAILURE
        )

        raise ConnectionError(
            "Invalid destination port: 0"
        )

    logger.info(
        "SOCKS request: %s %s:%s",
        address_type_name,
        address,
        port
    )

    return address, port


# ============================================================
# IPv4 Outbound Connection
# ============================================================

def create_remote(address, port):

    last_error = None

    try:

        # IMPORTANT:
        #
        # AF_INET forces IPv4 DNS resolution.
        #
        # This prevents Railway from selecting IPv6 addresses
        # such as:
        #
        # 2a03:2880:...
        #
        # which previously produced:
        #
        # [Errno 101] Network unreachable
        #

        addr_info = socket.getaddrinfo(
            address,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM
        )

    except socket.gaierror as exc:

        raise ConnectionError(
            f"IPv4 DNS resolution failed for {address}: {exc}"
        )

    if not addr_info:

        raise ConnectionError(
            f"No IPv4 address found for {address}"
        )

    # Remove duplicate addresses while preserving order.

    candidates = []

    seen = set()

    for item in addr_info:

        sockaddr = item[4]

        if sockaddr not in seen:

            seen.add(
                sockaddr
            )

            candidates.append(
                item
            )

    for (
        family,
        socktype,
        proto,
        _,
        sockaddr
    ) in candidates:

        remote = socket.socket(
            family,
            socktype,
            proto
        )

        remote.settimeout(
            CONNECT_TIMEOUT
        )

        try:

            logger.info(
                "Trying IPv4 connection to %s:%s",
                sockaddr[0],
                sockaddr[1]
            )

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

        except socket.timeout as exc:

            last_error = exc

            logger.warning(
                "IPv4 connection timeout to %s:%s",
                sockaddr[0],
                sockaddr[1]
            )

        except OSError as exc:

            last_error = exc

            logger.warning(
                "IPv4 connection failed to %s:%s: %s",
                sockaddr[0],
                sockaddr[1],
                exc
            )

        finally:

            if last_error is not None:

                try:
                    remote.close()
                except Exception:
                    pass

    raise ConnectionError(
        "Could not connect to destination via IPv4: "
        + str(last_error)
    )


# ============================================================
# Data Relay
# ============================================================

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
                RELAY_TIMEOUT
            )

        except Exception as exc:

            logger.warning(
                "Relay select error: %s",
                exc
            )

            return

        if exceptional:

            logger.info(
                "Relay socket exception"
            )

            return

        if not readable:

            logger.info(
                "Relay idle timeout"
            )

            return

        for sock in readable:

            try:

                data = sock.recv(
                    BUFFER_SIZE
                )

            except socket.timeout:

                return

            except OSError as exc:

                logger.warning(
                    "Relay receive error: %s",
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

            except OSError as exc:

                logger.warning(
                    "Relay send error: %s",
                    exc
                )

                return


# ============================================================
# Client Handler
# ============================================================

def handle_client(
    client,
    address
):

    remote = None

    client_ip = address[0]
    client_port = address[1]

    try:

        client.settimeout(
            CONNECT_TIMEOUT
        )

        logger.info(
            "Client connected: %s:%s",
            client_ip,
            client_port
        )

        # ----------------------------------------------------
        # SOCKS5 authentication
        # ----------------------------------------------------

        if not authenticate(
            client
        ):

            logger.warning(
                "SOCKS5 negotiation rejected: %s:%s",
                client_ip,
                client_port
            )

            return

        # ----------------------------------------------------
        # SOCKS5 CONNECT request
        # ----------------------------------------------------

        destination, port = parse_request(
            client
        )

        logger.info(
            "CONNECT %s:%s from %s:%s",
            destination,
            port,
            client_ip,
            client_port
        )

        # ----------------------------------------------------
        # Connect to destination using IPv4
        # ----------------------------------------------------

        try:

            remote = create_remote(
                destination,
                port
            )

        except ConnectionError as exc:

            error_text = str(
                exc
            ).lower()

            if (
                "timeout" in error_text
            ):

                reply = REP_TTL_EXPIRED

            elif (
                "refused" in error_text
            ):

                reply = REP_CONNECTION_REFUSED

            elif (
                "network unreachable" in error_text
            ):

                reply = REP_NETWORK_UNREACHABLE

            elif (
                "host" in error_text
            ):

                reply = REP_HOST_UNREACHABLE

            else:

                reply = REP_GENERAL_FAILURE

            send_reply(
                client,
                reply
            )

            raise

        # ----------------------------------------------------
        # SOCKS5 success
        # ----------------------------------------------------

        send_reply(
            client,
            REP_SUCCEEDED
        )

        client.settimeout(
            None
        )

        # ----------------------------------------------------
        # Start bidirectional relay
        # ----------------------------------------------------

        relay(
            client,
            remote
        )

    except ConnectionError as exc:

        logger.warning(
            "Connection error from %s:%s: %s",
            client_ip,
            client_port,
            exc
        )

    except Exception as exc:

        logger.exception(
            "Unexpected error from %s:%s: %s",
            client_ip,
            client_port
        )

    finally:

        try:
            client.close()
        except Exception:
            pass

        if remote is not None:

            try:
                remote.close()
            except Exception:
                pass

        logger.info(
            "Connection closed: %s:%s",
            client_ip,
            client_port
        )


# ============================================================
# Server
# ============================================================

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

        try:

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

        except KeyboardInterrupt:

            logger.info(
                "Server shutting down"
            )

            break

        except Exception as exc:

            logger.exception(
                "Accept loop error: %s",
                exc
            )

    try:
        server.close()
    except Exception:
        pass


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()
