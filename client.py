import socket
import threading
import struct
import os
import sys

HOST = '127.0.0.1'
PORT = 5000
CLIENT_DIR = 'client_files'

os.makedirs(CLIENT_DIR, exist_ok=True)

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

def listen_to_server(sock):
    """Background thread to handle ALL incoming messages and files."""
    try:
        while True:
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(1)
                if not chunk: break
                buf += chunk
            
            if not buf: break
            msg = buf.decode()
            
            if msg.startswith("FILE_READY"):
                filename = msg.split(" ")[1].strip()
                filepath = os.path.join(CLIENT_DIR, filename)
                print(f"\n[Server is sending file: {filename}]")
                
                recv_file(sock, filepath)
                print(f"\n[Download complete: {filename}]\n> ", end="", flush=True)
            else:
                print(f"\n{msg.strip()}\n> ", end="", flush=True)
    except Exception as e:
        print(f"\nDisconnected from server: {e}")
        sys.exit(0)

def run_client():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    print("Connected to server! Commands: /list, /upload <file>, /download <file>")
    
    listener = threading.Thread(target=listen_to_server, args=(client,), daemon=True)
    listener.start()

    while True:
        msg = input("> ")
        if not msg: continue
        
        parts = msg.split(" ", 1)
        cmd = parts[0]

        if cmd == "/upload" and len(parts) > 1:
            filename = os.path.basename(parts[1])           
            filepath = os.path.join(CLIENT_DIR, filename)   
            
            if not os.path.exists(filepath):
                print(f"Local file not found: {filepath}")
                continue
            
            client.sendall(f"{msg}\n".encode())
            send_file(client, filepath)
            print("File sent.")

        elif cmd == "/download" and len(parts) > 1:
            client.sendall(f"{msg}\n".encode())
        else:
            client.sendall(f"{msg}\n".encode())

if __name__ == "__main__":
    run_client()