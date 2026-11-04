import json
import socket
import threading
from typing import Optional

HOST = "0.0.0.0"
PORT = 55555
clients = {}
clients_lock = threading.Lock()


class ClientConnection:
    """A connected client and the public key it registered."""

    def __init__(self, sock):
        self.socket = sock
        self.nickname: Optional[str] = None
        self.n: Optional[int] = None
        self.e: Optional[int] = None
        self.send_lock = threading.Lock()

    def send(self, payload):
        data = json.dumps(payload).encode("utf-8") + b"\n"
        with self.send_lock:
            self.socket.sendall(data)


def send_roster():
    """Send the connected clients' public keys to every client."""
    with clients_lock:
        roster = [
            {"nickname": item.nickname, "n": item.n, "e": item.e}
            for item in clients.values()
        ]
        recipients = list(clients.values())

    for recipient in recipients:
        try:
            recipient.send({"type": "roster", "clients": roster})
        except OSError:
            try:
                recipient.socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def remove_client(connection):
    """Remove a disconnected client and announce the updated roster."""
    removed = False
    with clients_lock:
        if (connection.nickname is not None
                and clients.get(connection.nickname) is connection):
            del clients[connection.nickname]
            removed = True

    try:
        connection.socket.close()
    except OSError:
        pass

    if removed:
        print(f"{connection.nickname} disconnected")
        send_roster()


def handle_client(sock, address):
    """Register a client, then route recipient-specific ciphertexts."""
    connection = ClientConnection(sock)
    reader = sock.makefile("r", encoding="utf-8")
    registered = False

    try:
        registration_line = reader.readline()
        if not registration_line:
            return

        registration = json.loads(registration_line)
        if not isinstance(registration, dict):
            return

        nickname = registration.get("nickname", "")
        n = registration.get("n")
        e = registration.get("e")
        if (not isinstance(nickname, str) or not nickname.strip()
                or type(n) is not int or type(e) is not int
                or n <= 255 or e <= 0 or e >= n):
            connection.send({"type": "error", "message": "Invalid nickname or RSA public key."})
            return
        nickname = nickname.strip()

        with clients_lock:
            if nickname in clients:
                connection.send({"type": "error", "message": "That nickname is already connected."})
                return
            connection.nickname = nickname
            connection.n = n
            connection.e = e
            clients[nickname] = connection
            registered = True

        print(f"{nickname} connected from {address}")
        send_roster()

        for line in reader:
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(request, dict) or request.get("type") != "message":
                continue

            ciphertexts = request.get("ciphertexts")
            if not isinstance(ciphertexts, dict):
                continue

            for recipient_name, ciphertext in ciphertexts.items():
                if (not isinstance(recipient_name, str)
                        or not isinstance(ciphertext, list)
                        or any(type(value) is not int or value < 0 for value in ciphertext)):
                    continue
                with clients_lock:
                    recipient = clients.get(recipient_name)
                if recipient is not None:
                    try:
                        recipient.send({
                            "type": "message",
                            "from": nickname,
                            "ciphertext": ciphertext,
                        })
                    except OSError:
                        try:
                            recipient.socket.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"Connection error from {address}: {error}")
    finally:
        reader.close()
        if registered:
            remove_client(connection)
        else:
            sock.close()


def receive_connections():
    """Accept clients and give each connection its own handler thread."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on port {PORT} (all network interfaces)...")

        while True:
            client_socket, address = server.accept()
            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True,
            )
            thread.start()


if __name__ == "__main__":
    receive_connections()