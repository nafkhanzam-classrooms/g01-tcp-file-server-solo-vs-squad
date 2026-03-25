import socket
import struct
import os

HOST = '127.0.0.1'
PORT = 5000
SERVER_DIR = 'server_files'

os.makedirs(SERVER_DIR, exist_ok=True)

def send_file(sock, filepath):
    """Sends a file using chunked blocks of 4096 bytes."""
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk: break
            sock.sendall(struct.pack(">I", len(chunk)) + chunk)
    sock.sendall(struct.pack(">I", 0))

def recv_file(sock, filepath):
    """Receives a file using chunked blocks."""
    with open(filepath, "wb") as f:
        while True:
            header = sock.recv(4)
            if not header: break
            length = struct.unpack(">I", header)[0]
            
            if length == 0:
                break
                
            buf = b""
            while len(buf) < length:
                buf += sock.recv(length - len(buf))
            f.write(buf)

def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Sync Server listening on {HOST}:{PORT}...")

    while True:
        client_sock, addr = server.accept()
        print(f"Connected to {addr}. Other clients will be blocked.")
        
        try:
            while True:
                buf = b""
                while b"\n" not in buf:
                    chunk = client_sock.recv(1024)
                    if not chunk: break
                    buf += chunk
                
                if not buf: break
                
                command_line = buf.decode().strip()
                parts = command_line.split(" ", 1)
                cmd = parts[0]

                if cmd == "/list":
                    files = os.listdir(SERVER_DIR)
                    file_list = "\n".join(files) if files else "Server is empty."
                    client_sock.sendall(f"{file_list}\nDONE\n".encode())
                
                elif cmd == "/upload" and len(parts) > 1:
                    filename = os.path.basename(parts[1])
                    filepath = os.path.join(SERVER_DIR, filename)
                    recv_file(client_sock, filepath)
                    client_sock.sendall(b"Upload complete.\n")

                elif cmd == "/download" and len(parts) > 1:
                    filename = os.path.basename(parts[1])
                    filepath = os.path.join(SERVER_DIR, filename)
                    if os.path.exists(filepath):
                        # Send a clear header so the client knows a file is coming
                        client_sock.sendall(f"FILE_READY {filename}\n".encode())
                        send_file(client_sock, filepath)
                    else:
                        client_sock.sendall(b"ERROR: File not found\n")

                else:
                    client_sock.sendall(f"Server echoed: {command_line}\n".encode())

        except Exception as e:
            print(f"Error with client: {e}")
        finally:
            client_sock.close()
            print(f"Client {addr} disconnected. Ready for next client.")

if __name__ == "__main__":
    run_server()