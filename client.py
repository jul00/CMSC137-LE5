import getpass
import json
import socket
import sys
import threading

try:
    import msvcrt
except ImportError:
    msvcrt = None

PORT = 55555
peers = {}
peers_lock = threading.Lock()
roster_ready = threading.Event()


def send_json(sock, payload):
    """Send one newline-delimited JSON packet."""
    sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")


def read_private_exponent():
    """Read the private exponent, masking each digit with an asterisk on Windows."""
    prompt = "Enter your private exponent d (kept on this device): "
    if msvcrt is None:
        return getpass.getpass(prompt)

    sys.stdout.write(prompt)
    sys.stdout.flush()
    digits = []
    while True:
        char = msvcrt.getwch()
        if char in ("\r", "\n"):
            sys.stdout.write("\n")
            break
        if char == "\x03":
            raise KeyboardInterrupt
        if char in ("\x00", "\xe0"):
            msvcrt.getwch()  # Consume the second character for a special key.
            continue
        if char in ("\b", "\x7f"):
            if digits:
                digits.pop()
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        if char.isdigit():
            digits.append(char)
            sys.stdout.write("*")
            sys.stdout.flush()

    if not digits:
        raise ValueError("The private exponent cannot be empty.")
    return "".join(digits)


def encrypt_for_peer(message, public_key):
    """Apply textbook RSA to each UTF-8 byte for this classroom demo."""
    n, e = public_key
    return [pow(value, e, n) for value in message.encode("utf-8")]


def decrypt_from_peer(ciphertext, n, d):
    """Decrypt byte-wise textbook RSA ciphertext with this client's key."""
    plaintext_bytes = bytes(pow(value, d, n) for value in ciphertext)
    return plaintext_bytes.decode("utf-8")


def receive_messages(sock, nickname, n, d):
    """Receive roster updates and decrypt messages addressed to this client."""
    try:
        with sock.makefile("r", encoding="utf-8") as reader:
            for line in reader:
                try:
                    packet = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if packet.get("type") == "error":
                    print(f"Server: {packet.get('message', 'Unknown error')}")
                    break

                if packet.get("type") == "roster":
                    updated_peers = {}
                    for peer in packet.get("clients", []):
                        peer_name = peer.get("nickname")
                        if peer_name != nickname:
                            updated_peers[peer_name] = (peer["n"], peer["e"])
                    with peers_lock:
                        peers.clear()
                        peers.update(updated_peers)
                    print("Connected peers:", ", ".join(updated_peers) or "none yet")
                    roster_ready.set()
                elif packet.get("type") == "message":
                    try:
                        text = decrypt_from_peer(packet["ciphertext"], n, d)
                        print(f"\n{packet.get('from', 'Unknown')}: {text}")
                    except (KeyError, TypeError, ValueError, UnicodeDecodeError):
                        print("\nCould not decrypt a received message; check the key pair.")
    except OSError as error:
        print(f"Connection closed: {error}")
    finally:
        roster_ready.set()
        try:
            sock.close()
        except OSError:
            pass


def write_messages(sock):
    """Encrypt a separate copy for each connected peer and send the packet."""
    roster_ready.wait()
    while True:
        try:
            text = input()
        except (EOFError, OSError):
            break

        if text.strip().lower() == "/quit":
            break

        with peers_lock:
            current_peers = dict(peers)
        if not current_peers:
            print("No other clients are connected yet.")
            continue

        packet = {
            "type": "message",
            "ciphertexts": {
                peer_name: encrypt_for_peer(text, public_key)
                for peer_name, public_key in current_peers.items()
            },
        }
        try:
            send_json(sock, packet)
        except OSError as error:
            print(f"Could not send message: {error}")
            break

    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def main():
    nickname = input("Choose your nickname: ").strip()
    n = int(input("Enter your public modulus n: ").strip())
    e = int(input("Enter your public exponent e: ").strip())
    d = int(read_private_exponent())
    if n <= 255 or e <= 0 or d <= 0:
        raise ValueError("Invalid RSA key values; n must be greater than 255 and e/d must be positive.")

    host = input("Server IP address [127.0.0.1]: ").strip() or "127.0.0.1"
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, PORT))
    send_json(client, {"type": "register", "nickname": nickname, "n": n, "e": e})

    receive_thread = threading.Thread(
        target=receive_messages,
        args=(client, nickname, n, d),
        daemon=True,
    )
    receive_thread.start()
    print("Chat connected. Type /quit to leave.")
    write_messages(client)


if __name__ == "__main__":
    main()
