import socket
import threading
import struct
import os

HOST = '127.0.0.1'
PORT = 5000
SERVER_DIR = 'server_files'

os.makedirs(SERVER_DIR, exist_ok=True)

active_clients = []

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

def broadcast(sender_sock, message):
    for client in active_clients:
        if client != sender_sock:
            try:
                client.sendall(message)
            except:
                pass

def client_handler(client_sock, client_addr):
    """This function runs in its own thread for EVERY connected client."""
    print(f"[NEW THREAD] Handling {client_addr}")
    broadcast(client_sock, f"[Server] Client {client_addr[1]} joined the chat.\n".encode())
    
    try:
        while True:
            buf = b""
            while b"\n" not in buf:
                chunk = client_sock.recv(1)
                if not chunk: break
                buf += chunk
            
            if not buf:
                break
            
            msg = buf.decode().strip()
            parts = msg.split(" ", 1)
            cmd = parts[0]

            if cmd == "/list":
                files = os.listdir(SERVER_DIR)
                file_list = "\n".join(files) if files else "Server is empty."
                client_sock.sendall(f"--- Server Files ---\n{file_list}\n--------------------\n".encode())
            
            elif cmd == "/upload" and len(parts) > 1:
                filename = os.path.basename(parts[1])
                filepath = os.path.join(SERVER_DIR, filename)
                print(f"Receiving {filename} from {client_addr[1]}...")
                recv_file(client_sock, filepath)
                client_sock.sendall(f"Successfully uploaded {filename}.\n".encode())
                broadcast(client_sock, f"[Server] A new file was uploaded: {filename}\n".encode())

            elif cmd == "/download" and len(parts) > 1:
                filename = os.path.basename(parts[1])
                filepath = os.path.join(SERVER_DIR, filename)
                if os.path.exists(filepath):
                    print(f"Sending {filename} to {client_addr[1]}...")
                    client_sock.sendall(f"FILE_READY {filename}\n".encode())
                    send_file(client_sock, filepath)
                else:
                    client_sock.sendall(b"ERROR: File not found on server.\n")

            else:
                formatted_msg = f"[Client {client_addr[1]}]: {msg}\n".encode()
                broadcast(client_sock, formatted_msg)
                
    except Exception as e:
        print(f"Error with {client_addr}: {e}")
    finally:
        print(f"Client {client_addr} disconnected. Thread terminating.")
        if client_sock in active_clients:
            active_clients.remove(client_sock)
        client_sock.close()
        broadcast(client_sock, f"[Server] Client {client_addr[1]} left the chat.\n".encode())


def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    
    print(f"Threaded Server listening on {HOST}:{PORT}...")

    try:
        while True:
            client_sock, client_addr = server.accept()
            
            active_clients.append(client_sock)
            
            client_thread = threading.Thread(target=client_handler, args=(client_sock, client_addr))
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.close()

if __name__ == "__main__":
    run_server()