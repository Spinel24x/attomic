#!/usr/bin/env python3

import os
import socket
import struct
import threading
import logging
import time


# ============================================================
# CONFIG
# ============================================================

HOST = "0.0.0.0"

# Railway normally provides PORT.
# If PORT is not present, use 53 for your current setup.
PORT = int(os.environ.get("PORT", "53"))

BUFFER_SIZE = 128 * 1024

CONNECT_TIMEOUT = 20

SOCKET_TIMEOUT = 60

# Optional authentication.
# Leave unset for no authentication.
USERNAME = os.environ.get("SOCKS5_USERNAME")
PASSWORD = os.environ.get("SOCKS5_PASSWORD")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("socks5")


# ============================================================
# SOCKS5 CONSTANTS
# ============================================================

SOCKS_VERSION = 5

NO_AUTH = 0x00
USERPASS_AUTH = 0x02
NO_ACCEPTABLE_AUTH = 0xFF

CMD_CONNECT = 0x01
CMD_BIND = 0x02
CMD_UDP_ASSOCIATE = 0x03

ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04

REP_SUCCESS = 0x00
REP_GENERAL_FAILURE = 0x01
REP_NOT_ALLOWED = 0x02
REP_NETWORK_UNREACHABLE = 0x03
REP_HOST_UNREACHABLE = 0x04
REP_CONNECTION_REFUSED = 0x05
REP_TTL_EXPIRED = 0x06
REP_COMMAND_NOT_SUPPORTED = 0x07
REP_ADDRESS_TYPE_NOT_SUPPORTED = 0x08


# ============================================================
# SOCKET TUNING
# ============================================================

def tune_socket(sock):
    """
    Tune TCP sockets for long-lived proxy traffic.
    """

    try:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_KEEPALIVE,
            1
        )
    except Exception:
        pass

    try:
        sock.setsockopt(
            socket.IPPROTO_TCP,
            socket.TCP_NODELAY,
            1
        )
    except Exception:
        pass

    try:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_RCVBUF,
            1024 * 1024
        )
    except Exception:
        pass

    try:
        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_SNDBUF,
            1024 * 1024
        )
    except Exception:
        pass


# ============================================================
# RECEIVE EXACTLY N BYTES
# ============================================================

def recv_exact(sock, size):

    data = bytearray()

    while len(data) < size:

        chunk = sock.recv(
            size - len(data)
        )

        if not chunk:
            raise ConnectionError(
                "Peer closed connection"
            )

        data.extend(chunk)

    return bytes(data)


# ============================================================
# SOCKS5 REPLY
# ============================================================

def send_reply(client, code):

    # Reply address is 0.0.0.0:0.
    #
    # For CONNECT this is valid because the client does not
    # require the proxy's bound address for normal operation.

    response = (
        b"\x05"
        + bytes([code])
        + b"\x00"
        + b"\x01"
        + socket.inet_aton("0.0.0.0")
        + struct.pack(">H", 0)
    )

    client.sendall(response)


# ============================================================
# AUTHENTICATION
# ============================================================

def negotiate_auth(client):

    header = recv_exact(
        client,
        2
    )

    version = header[0]
    method_count = header[1]

    if version != SOCKS_VERSION:

        raise ConnectionError(
            f"Invalid SOCKS version: {version}"
        )

    methods = recv_exact(
        client,
        method_count
    )

    authentication_enabled = (
        USERNAME is not None
        and PASSWORD is not None
    )

    # --------------------------------------------------------
    # Username / Password
    # --------------------------------------------------------

    if authentication_enabled:

        if USERPASS_AUTH not in methods:

            client.sendall(
                b"\x05\xff"
            )

            raise ConnectionError(
                "Client does not support username/password"
            )

        client.sendall(
            b"\x05\x02"
        )

        auth_version = recv_exact(
            client,
            1
        )[0]

        if auth_version != 1:

            raise ConnectionError(
                "Invalid username/password auth version"
            )

        username_length = recv_exact(
            client,
            1
        )[0]

        username_raw = recv_exact(
            client,
            username_length
        )

        password_length = recv_exact(
            client,
            1
        )[0]

        password_raw = recv_exact(
            client,
            password_length
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

            raise ConnectionError(
                "Invalid username/password"
            )

        client.sendall(
            b"\x01\x00"
        )

        return

    # --------------------------------------------------------
    # No authentication
    # --------------------------------------------------------

    if NO_AUTH not in methods:

        client.sendall(
            b"\x05\xff"
        )

        raise ConnectionError(
            "Client does not support no-authentication"
        )

    client.sendall(
        b"\x05\x00"
    )


# ============================================================
# PARSE SOCKS5 REQUEST
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

    if version != SOCKS_VERSION:

        send_reply(
            client,
            REP_GENERAL_FAILURE
        )

        raise ConnectionError(
            "Invalid SOCKS version"
        )

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    if command != CMD_CONNECT:

        if command == CMD_UDP_ASSOCIATE:

            logger.warning(
                "UDP ASSOCIATE requested; UDP proxying is not enabled"
            )

        else:

            logger.warning(
                "Unsupported SOCKS5 command: %s",
                command
            )

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

    if address_type == ATYP_IPV4:

        raw = recv_exact(
            client,
            4
        )

        address = socket.inet_ntoa(
            raw
        )

        address_type_name = "IPv4"

    # --------------------------------------------------------
    # DOMAIN
    # --------------------------------------------------------

    elif address_type == ATYP_DOMAIN:

        length = recv_exact(
            client,
            1
        )[0]

        if length == 0:

            send_reply(
                client,
                REP_GENERAL_FAILURE
            )

            raise ConnectionError(
                "Empty domain"
            )

        raw = recv_exact(
            client,
            length
        )

        # Do NOT use:
        #
        # decode("idna", errors="ignore")
        #
        # Python's IDNA codec does not support that
        # error handler.
        #
        # SOCKS5 normally sends the domain as ASCII.

        address = raw.decode(
            "ascii",
            errors="replace"
        )

        address_type_name = "DOMAIN"

    # --------------------------------------------------------
    # IPv6
    # --------------------------------------------------------

    elif address_type == ATYP_IPV6:

        raw = recv_exact(
            client,
            16
        )

        address = socket.inet_ntop(
            socket.AF_INET6,
            raw
        )

        logger.warning(
            "IPv6 destination requested: %s",
            address
        )

        send_reply(
            client,
            REP_NETWORK_UNREACHABLE
        )

        raise ConnectionError(
            f"IPv6 outbound unavailable: {address}"
        )

    else:

        send_reply(
            client,
            REP_ADDRESS_TYPE_NOT_SUPPORTED
        )

        raise ConnectionError(
            f"Unsupported address type: {address_type}"
        )

    # --------------------------------------------------------
    # PORT
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
            "Destination port is zero"
        )

    logger.info(
        "SOCKS request: %s %s:%d",
        address_type_name,
        address,
        port
    )

    return address, port


# ============================================================
# CONNECT USING IPV4 ONLY
# ============================================================

def connect_ipv4(host, port):

    try:

        results = socket.getaddrinfo(
            host,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM,
            0,
            socket.AI_ADDRCONFIG
        )

    except socket.gaierror:

        # Some environments behave better without
        # AI_ADDRCONFIG.

        try:

            results = socket.getaddrinfo(
                host,
                port,
                socket.AF_INET,
                socket.SOCK_STREAM
            )

        except socket.gaierror as exc:

            raise ConnectionError(
                f"IPv4 DNS resolution failed: {exc}"
            )

    if not results:

        raise ConnectionError(
            f"No IPv4 address for {host}"
        )

    last_error = None

    tried = set()

    for result in results:

        family = result[0]
        socktype = result[1]
        proto = result[2]
        sockaddr = result[4]

        if sockaddr in tried:
            continue

        tried.add(
            sockaddr
        )

        remote = socket.socket(
            family,
            socktype,
            proto
        )

        tune_socket(
            remote
        )

        remote.settimeout(
            CONNECT_TIMEOUT
        )

        try:

            logger.info(
                "Trying IPv4 connection to %s:%d",
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
                "Connected to %s:%d via IPv4",
                host,
                port
            )

            return remote

        except Exception as exc:

            last_error = exc

            logger.warning(
                "IPv4 connection failed to %s:%d: %s",
                sockaddr[0],
                sockaddr[1],
                exc
            )

            try:
                remote.close()
            except Exception:
                pass

    raise ConnectionError(
        f"Could not connect to {host}:{port}: {last_error}"
    )


# ============================================================
# ONE-WAY RELAY
# ============================================================

def relay_direction(
    source,
    destination,
    direction_name,
    counter,
    stop_event
):

    total = 0

    try:

        while not stop_event.is_set():

            try:

                data = source.recv(
                    BUFFER_SIZE
                )

            except socket.timeout:

                continue

            except (ConnectionResetError, BrokenPipeError):

                break

            except OSError as exc:

                logger.warning(
                    "Relay %s receive error: %s",
                    direction_name,
                    exc
                )

                break

            if not data:

                break

            try:

                destination.sendall(
                    data
                )

            except (
                ConnectionResetError,
                BrokenPipeError
            ):

                break

            except OSError as exc:

                logger.warning(
                    "Relay %s send error: %s",
                    direction_name,
                    exc
                )

                break

            total += len(data)

            counter["bytes"] = total

            # Log the first data packet immediately.
            if total == len(data):

                logger.info(
                    "Relay %s started: %d bytes",
                    direction_name,
                    len(data)
                )

    except Exception as exc:

        logger.warning(
            "Relay %s unexpected error: %s",
            direction_name,
            exc
        )

    finally:

        stop_event.set()

        logger.info(
            "Relay %s stopped: %d bytes transferred",
            direction_name,
            total
        )


# ============================================================
# BIDIRECTIONAL TCP RELAY
# ============================================================

def relay(client, remote):

    stop_event = threading.Event()

    client_counter = {
        "bytes": 0
    }

    remote_counter = {
        "bytes": 0
    }

    # --------------------------------------------------------
    # Do NOT use aggressive socket timeouts here.
    #
    # A SOCKS tunnel can legitimately remain idle.
    # --------------------------------------------------------

    client.settimeout(
        None
    )

    remote.settimeout(
        None
    )

    tune_socket(
        client
    )

    tune_socket(
        remote
    )

    t1 = threading.Thread(
        target=relay_direction,
        args=(
            client,
            remote,
            "CLIENT -> REMOTE",
            client_counter,
            stop_event
        ),
        daemon=True
    )

    t2 = threading.Thread(
        target=relay_direction,
        args=(
            remote,
            client,
            "REMOTE -> CLIENT",
            remote_counter,
            stop_event
        ),
        daemon=True
    )

    start = time.monotonic()

    t1.start()
    t2.start()

    # --------------------------------------------------------
    # Keep relay alive until one side terminates.
    # --------------------------------------------------------

    while not stop_event.wait(
        1
    ):

        # Log transfer statistics every ~10 seconds.

        elapsed = time.monotonic() - start

        if (
            int(elapsed) > 0
            and
            int(elapsed) % 10 == 0
        ):

            logger.info(
                "Traffic stats: client->remote=%d bytes, "
                "remote->client=%d bytes",
                client_counter["bytes"],
                remote_counter["bytes"]
            )

    # --------------------------------------------------------
    # Shutdown both directions.
    # --------------------------------------------------------

    try:
        client.shutdown(
            socket.SHUT_RDWR
        )
    except Exception:
        pass

    try:
        remote.shutdown(
            socket.SHUT_RDWR
        )
    except Exception:
        pass

    t1.join(
        timeout=2
    )

    t2.join(
        timeout=2
    )

    logger.info(
        "Tunnel finished: client->remote=%d bytes, "
        "remote->client=%d bytes",
        client_counter["bytes"],
        remote_counter["bytes"]
    )


# ============================================================
# CLIENT HANDLER
# ============================================================

def handle_client(
    client,
    address
):

    remote = None

    client_ip = address[0]
    client_port = address[1]

    try:

        tune_socket(
            client
        )

        logger.info(
            "Client connected: %s:%d",
            client_ip,
            client_port
        )

        # ----------------------------------------------------
        # SOCKS negotiation
        # ----------------------------------------------------

        client.settimeout(
            CONNECT_TIMEOUT
        )

        negotiate_auth(
            client
        )

        # ----------------------------------------------------
        # Request
        # ----------------------------------------------------

        destination, port = parse_request(
            client
        )

        logger.info(
            "CONNECT %s:%d from %s:%d",
            destination,
            port,
            client_ip,
            client_port
        )

        # ----------------------------------------------------
        # Remote connection
        # ----------------------------------------------------

        try:

            remote = connect_ipv4(
                destination,
                port
            )

        except ConnectionError as exc:

            text = str(
                exc
            ).lower()

            if "refused" in text:

                code = REP_CONNECTION_REFUSED

            elif "network unreachable" in text:

                code = REP_NETWORK_UNREACHABLE

            elif "host" in text:

                code = REP_HOST_UNREACHABLE

            elif "timeout" in text:

                code = REP_TTL_EXPIRED

            else:

                code = REP_GENERAL_FAILURE

            try:

                send_reply(
                    client,
                    code
                )

            except Exception:
                pass

            raise

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        send_reply(
            client,
            REP_SUCCESS
        )

        logger.info(
            "SOCKS5 CONNECT established: %s:%d",
            destination,
            port
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # The handshake timeout must NOT remain active during
        # the actual tunnel.
        # ----------------------------------------------------

        client.settimeout(
            None
        )

        remote.settimeout(
            None
        )

        # ----------------------------------------------------
        # Relay
        # ----------------------------------------------------

        relay(
            client,
            remote
        )

    except Exception as exc:

        logger.warning(
            "Connection error from %s:%d: %s",
            client_ip,
            client_port,
            exc
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
            "Connection closed: %s:%d",
            client_ip,
            client_port
        )


# ============================================================
# SERVER
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

    try:

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_KEEPALIVE,
            1
        )

    except Exception:
        pass

    server.bind(
        (
            HOST,
            PORT
        )
    )

    server.listen(
        512
    )

    logger.info(
        "SOCKS5 server listening on %s:%d",
        HOST,
        PORT
    )

    while True:

        try:

            client, address = server.accept()

            logger.info(
                "TCP connection accepted from %s:%d",
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

            break

        except Exception as exc:

            logger.exception(
                "Accept error: %s",
                exc
            )

    server.close()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()
