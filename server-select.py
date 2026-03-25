import socket
import select
import struct
import os

HOST = '127.0.0.1'
PORT = 5000
SERVER_DIR = 'server_files'

os.makedirs(SERVER_DIR, exist_ok=True)

def send_file(sock, filepath):
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk: break
            sock.sendall(struct.pack(">I", len(chunk)) + chunk)
    sock.sendall(struct.pack(">I", 0))

def recv_file(sock, filepath):
    with open(filepath, "wb") as f:
        while True:
            header = sock.recv(4)
            if not header: break
            length = struct.unpack(">I", header)[0]
            if length == 0: break
            buf = b""
            while len(buf) < length:
                buf += sock.recv(length - len(buf))
            f.write(buf)

def broadcast(sender_sock, active_clients, message):
    """Sends a message to all clients except the sender."""
    for client in active_clients:
        if client != sender_sock:
            try:
                client.sendall(message)
            except:
                pass

def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    print(f"Select Server listening on {HOST}:{PORT}...")

    inputs = [server_socket]
    clients = []

    while True:
        read_ready, _, _ = select.select(inputs, [], [])

        for sock in read_ready:
            if sock == server_socket:
                client_sock, client_addr = server_socket.accept()
                inputs.append(client_sock)
                clients.append(client_sock)
                print(f"Connected: {client_addr}")
                broadcast(server_socket, clients, f"[Server] Client {client_addr[1]} joined the chat.\n".encode())

            else:
                try:
                    buf = b""
                    while b"\n" not in buf:
                        chunk = sock.recv(1)
                        if not chunk: break
                        buf += chunk
                    
                    if not buf:
                        raise ConnectionResetError
                    
                    msg = buf.decode().strip()
                    parts = msg.split(" ", 1)
                    cmd = parts[0]

                    if cmd == "/list":
                        files = os.listdir(SERVER_DIR)
                        file_list = "\n".join(files) if files else "Server is empty."
                        sock.sendall(f"--- Server Files ---\n{file_list}\n--------------------\n".encode())
                    
                    elif cmd == "/upload" and len(parts) > 1:
                        filename = os.path.basename(parts[1])
                        filepath = os.path.join(SERVER_DIR, filename)
                        print(f"Receiving {filename}...")
                        recv_file(sock, filepath)
                        sock.sendall(f"Successfully uploaded {filename}.\n".encode())
                        broadcast(sock, clients, f"[Server] A new file was uploaded: {filename}\n".encode())

                    elif cmd == "/download" and len(parts) > 1:
                        filename = os.path.basename(parts[1])
                        filepath = os.path.join(SERVER_DIR, filename)
                        if os.path.exists(filepath):
                            print(f"Sending {filename}...")
                            sock.sendall(f"FILE_READY {filename}\n".encode())
                            send_file(sock, filepath)
                        else:
                            sock.sendall(b"ERROR: File not found on server.\n")

                    else:
                        formatted_msg = f"[Client {sock.getpeername()[1]}]: {msg}\n".encode()
                        broadcast(sock, clients, formatted_msg)
                        
                except Exception as e:
                    addr = sock.getpeername()
                    print(f"Client {addr} disconnected.")
                    inputs.remove(sock)
                    clients.remove(sock)
                    sock.close()
                    broadcast(server_socket, clients, f"[Server] Client {addr[1]} left the chat.\n".encode())

if __name__ == "__main__":
    run_server()