# sender.py
# Sender (client): sends one precinct's votes to the receiver using CRC.

import socket
from crc_module import encode_data

HOST = "127.0.0.1"   # change to the IP of the computer running the receiver
PORT = 65432         # must be the same as the receiver's port
KEY = "1001"         # CRC key, must be the same as the receiver's key


def ask_number(prompt):
    # Keep asking until the user types a whole number
    while True:
        value = input(prompt)
        if value.isdigit():
            return int(value)
        print("Please enter a whole number.")


# 1. Get the data from the user
area = input("Area code: ")

nominees = {}
count = ask_number("Number of nominees: ")
for i in range(count):
    name = input(f"Nominee {i + 1} name: ")
    votes = ask_number(f"Votes for {name}: ")
    nominees[name] = votes

eligible = ask_number("Total eligible voters: ")

# 2. Put each value in its own line using the format the receiver expects
messages = ["AREA|" + area]
for name, votes in nominees.items():
    messages.append("NOMINEE|" + name + "|" + str(votes))
messages.append("ELIGIBLE|" + str(eligible))

# 3. Encode every line with CRC
codewords = []
for msg in messages:
    bits, _ = encode_data(msg, KEY)
    codewords.append(bits)

# 4. Send all codewords to the receiver, one per line
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
client.sendall("\n".join(codewords).encode())
client.shutdown(socket.SHUT_WR)   # tells the receiver we are done sending

# 5. Show the status message (ACK or NACK) from the receiver
response = client.recv(1024).decode()
print("Receiver says:", response)

client.close()
