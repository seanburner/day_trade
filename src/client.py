import socket

def main() -> None :
    HOST = '127.0.0.1'  # The server's hostname or IP address
    PORT = 65432        # The port used by the server

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b"email\0\0")
        data = s.recv(1024)
        print(f"[CLIENT] Received from server: {data.decode()}")

if __name__ == "__main__":
    # execute only if run as a script        
    main()  
