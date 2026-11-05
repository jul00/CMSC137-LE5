# The receiver tallies the election. Each sender is one precinct (area code).
# For every sender it:
#   1. receives the area code, each nominee's votes, and the eligible voters (every value is sent as its own CRC codeword, one per line),
#   2. checks every codeword with CRC; if ANY fails, the whole sender's data is discarded and a NACK is sent back,
#   3. otherwise adds the votes to the running totals, sends an ACK, and shows the updated results.

import socket
from crc_module import mod2div

HOST = "172.20.10.3"   # IP of the computer running the receiver (same as sender)
PORT = 65432         # must be equal to the sender's port
KEY = "1001"         # CRC key (same as sender)

votes = {}           # nominee -> total votes from all senders so far
eligible_total = 0   # total eligible voters from all senders so far


def decode(bits):
    """Check a codeword with CRC and return its text, or None if corrupted."""
    if "1" in mod2div(bits, KEY):                   # remainder must be all zeros
        return None
    data = bits[:-(len(KEY) - 1)]                   # remove the CRC bits
    return "".join(chr(int(data[i:i + 8], 2)) for i in range(0, len(data), 8))


def show_results():
    """Show every nominee (highest first), then the voter turnout."""
    total = sum(votes.values())
    print("\n----- RESULTS -----")
    for name, count in sorted(votes.items(), key=lambda x: x[1], reverse=True):
        print(f"{name}: {count} votes ({count / max(total, 1) * 100:.2f}%)")
    print(f"Voters who voted: {total}")
    print(f"Eligible voters : {eligible_total}")
    print(f"Percent who voted: {total / max(eligible_total, 1) * 100:.2f}%\n")


def handle(conn):
    """Receive one sender's data; count it only if every CRC check passes."""
    global eligible_total

    data = ""
    while True:                                     # read until the sender is done
        chunk = conn.recv(4096).decode()
        if not chunk:
            break
        data += chunk

    try:
        area, eligible, new_votes = None, 0, {}
        for bits in data.split():                   # one codeword per line
            text = decode(bits)
            if text is None:
                raise ValueError("CRC error")
            kind, *parts = text.split("|")          # e.g. NOMINEE|Maria|1200
            if kind == "AREA":
                area = parts[0]
            elif kind == "NOMINEE":
                new_votes[parts[0]] = int(parts[1])
            elif kind == "ELIGIBLE":
                eligible = int(parts[0])
    except (ValueError, IndexError):
        print("Error detected. Data from this sender discarded.")
        conn.sendall(b"NACK: Error detected. All data discarded.")
        return

    for name, count in new_votes.items():           # add this precinct to the totals
        votes[name] = votes.get(name, 0) + count
    eligible_total += eligible
    print(f"Area {area} received and counted.")
    conn.sendall(f"ACK: Area {area} received.".encode())
    show_results()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # allow quick restart
    server.bind((HOST, PORT))
    server.listen()
    server.settimeout(1.0)                          # wake up every second so Ctrl+C works on Windows
    print(f"Receiver listening on {HOST}:{PORT} (Ctrl+C to stop)")
    try:
        while True:                                 # one sender (precinct) at a time
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue                            # no sender yet, check again
            with conn:
                conn.settimeout(None)               # accepted socket inherits the timeout; turn it off
                handle(conn)
    except KeyboardInterrupt:
        print("\nReceiver stopped.")
