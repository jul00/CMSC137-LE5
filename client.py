import socket
import threading

# Get user configuration
nickname = input("Choose your nickname: ")

# Server configuration to connect to
HOST = '127.0.0.1'
PORT = 55555

# Connect to the server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

def receive_messages():
    """Constantly listens for messages from the server."""
    while True:
        try:
            # Receive and decode data from the server
            message = client.recv(1024).decode('utf-8')
            print(message)
        except:
            # Close connection if an error occurs
            print("An error occurred! Disconnecting...")
            client.close()
            break

def write_messages():
    """Constantly waits for user input to send to the server."""
    while True:
        try:
            user_input = input("")
            # Format message with nickname
            full_message = f"{nickname}: {user_input}"
            client.send(full_message.encode('utf-8'))
        except:
            client.close()
            break

# Start thread for receiving messages
receive_thread = threading.Thread(target=receive_messages)
receive_thread.start()

# Start thread for sending messages
write_thread = threading.Thread(target=write_messages)
write_thread.start()
