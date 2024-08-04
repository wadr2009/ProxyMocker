import socket
import time

def check_port(host, port):
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                print(f"Port {port} is open")
                return True
        except (socket.timeout, ConnectionRefusedError):
            print(f"Port {port} is not open yet, retrying in 0.5 seconds")
            time.sleep(0.5)
        except OSError as e:
            print(f"Error connecting to {host}:{port}: {e}")
            time.sleep(0.5)


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8800
    print(f"Checking if port {port} is open on {host}")
    check_port(host, port)
