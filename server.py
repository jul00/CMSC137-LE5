import socket
import threading

# Server configuration
HOST = '127.0.0.1'  # Localhost
PORT = 55555        # Choose any free port above 1023

# Initialize the TCP server socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Prevents "port already in use" errors
server.bind((HOST, PORT))
server.listen()

# Track active client sockets
clients = []

def broadcast(message, sender_client):
    """Sends a message to all connected clients except the sender."""
    for client in clients:
        if client != sender_client:
            try:
                client.send(message)
            except:
                # Remove broken client connections
                remove_client(client)

def remove_client(client):
    """Removes a client from the list and closes the socket safely."""
    if client in clients:
        clients.remove(client)
        client.close()

def handle_client(client):
    """Listens for incoming messages from a specific client."""
    while True:
        try:
            # Receive message from client (up to 1024 bytes)
            message = client.recv(1024)
            if not message:
                break
            # Broadcast the received message to everyone else
            broadcast(message, client)
        except:
            break
    
    remove_client(client)

def receive_connections():
    """Main loop to accept incoming client connections."""
    print(f"Server is running and listening on {HOST}:{PORT}...")
    while True:
        # Accept a new connection
        client, address = server.accept()
        print(f"Connected with {str(address)}")

        # Keep track of the client
        clients.append(client)

        # Start a dedicated thread to handle this specific client
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

if __name__ == "__main__":
    receive_connections()
