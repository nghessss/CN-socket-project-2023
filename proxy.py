from socket import *
import sys
import threading
import os
import time
from datetime import datetime

# Whitelisted websites
whitelist = ["example.com", "example2.com"]  # Add allowed websites here

# Cache directory for storing images
cache_directory = "cache"
if not os.path.exists(cache_directory):
    os.makedirs(cache_directory)

# Set caching time for images (in seconds)
cache_time = 900  # 1 hour

# Dictionary to track the last access time of websites
last_access_time = {}

# Read config file to get server IP and port
def read_config_file(filename):
    with open(filename, "r") as file:
        config_data = file.read().splitlines()
        server_ip = config_data[0].split("=")[1].strip()
        server_port = int(config_data[1].split("=")[1].strip())
        return server_ip, server_port

# Function to check if a website is whitelisted
def is_whitelisted(host):
    return any(host.endswith(allowed_host) for allowed_host in whitelist)

def read_response403(filename):
    if filename == "custom403.html":
        with open("custom403.html", "rb") as html_file:
            content = html_file.read()
            response = b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/html\r\n\r\n" + content
    return response

# Function to check if the current time is within the allowed hours (8 AM to 8 PM)
def is_within_allowed_time():
    now = datetime.now().time()
    return now >= datetime.strptime("08:00:00", "%H:%M:%S").time() and now <= datetime.strptime("20:00:00", "%H:%M:%S").time()

# Function to handle concurrent client connections
def handle_client(tcpCliSock):
    # Receive the HTTP request from the client
    message = tcpCliSock.recv(1024).decode()
    print("Received request:\n", message)

    # Extract the HTTP method from the request
    http_method = message.split()[0]
    print("HTTP method:", http_method)

    # Extract the requested filename from the HTTP request
    filename = message.split()[1].partition("/")[2]
    print("Requested filename:", filename)

    # Check if the requested website is whitelisted
    host = filename.split("/")[0]

    if not is_within_allowed_time():
        # response = response403()
        response = read_response403("custom403.html")
    elif not is_whitelisted(host):
        # response = response403() 
        response = read_response403("custom403.html")
    elif http_method not in ["GET", "POST", "HEAD"]:
        # Return 405 Method Not Allowed with custom HTML content
        response = b"HTTP/1.0 405 Method Not Allowed\r\nContent-Type: text/html\r\n\r\n"
        response += b"<html><body><h1>405 Method Not Allowed</h1>"
        response += b"<p>You are not allowed to use this HTTP method.</p>"
        response += b"</body></html>"
    else:
        # Check if the requested image is in the cache and not expired
        image_path = os.path.join(cache_directory, filename)
        if http_method == "GET" and os.path.exists(image_path):
            current_time = time.time()
            if filename in last_access_time and current_time - last_access_time[filename] < cache_time:
                # Serve the image from the cache
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()

                response = b"HTTP/1.0 200 OK\r\nContent-Type: image/jpeg\r\n\r\n" + image_data
                print("Read from cache:", filename)
            else:
                # The image is expired in the cache, fetch it from the web server
                response = fetch_from_web_server(message, filename)

                # Update the cache with the new image
                if response.startswith(b"HTTP/1.0 200 OK"):
                    with open(image_path, "wb") as image_file:
                        image_file.write(response)

                last_access_time[filename] = current_time
        else:
            # Fetch the image from the web server
            response = fetch_from_web_server(message, filename)

            # Cache the image if it is a successful response
            if response.startswith(b"HTTP/1.0 200 OK"):
                with open(image_path, "wb") as image_file:
                    image_file.write(response)

                last_access_time[filename] = time.time()

    # Send the response back to the client
    tcpCliSock.send(response)

    # Close the client socket after processing the request
    tcpCliSock.close()

# Function to fetch an image from the web server
def fetch_from_web_server(request, filename):
    try:
        # Create a socket to connect to the web server
        c = socket(AF_INET, SOCK_STREAM)
        host = filename.split("/")[0]
        web_port = 80

        # Connect to the web server on port 80
        c.connect((host, web_port))

        # Send the HTTP request to the web server
        c.send(request.encode())

        # Receive the response from the web server
        response = b""
        while True:
            data = c.recv(1024)
            if not data:
                break
            response += data

        # Close the connection to the web server
        c.close()

        return response

    except:
        # Error handling for failed requests to the web server
        response = b"HTTP/1.0 404 Not Found\r\nContent-Type: text/html\r\n\r\n404 Not Found"
        return response

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print('Usage : "python ProxyServer.py config_file"\n[config_file : Path to the configuration file]')
        sys.exit(2)

    # Read the server IP and port from the config file
    config_file = sys.argv[1]
    server_ip, server_port = read_config_file(config_file)

    # Create a server socket, bind it to the server IP and port, and start listening
    tcpSerSock = socket(AF_INET, SOCK_STREAM)
    tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    tcpSerSock.bind((server_ip, server_port))
    tcpSerSock.listen(5)  # Maximum number of queued connections is set to 5

    print('Proxy server is ready to receive connections...')

    # Define a function to handle incoming client connections
    def start_proxy():
        while True:
            # Accept a new client connection
            try:
                tcpCliSock, addr = tcpSerSock.accept()
                print('Received a connection from:', addr)

                # Create a new thread to handle the client request
                client_thread = threading.Thread(target=handle_client, args=(tcpCliSock,))
                client_thread.start()

            except KeyboardInterrupt:
                # If Ctrl + C is pressed, close the proxy server gracefully
                print("\nProxy server is shutting down...")
                tcpSerSock.close()
                sys.exit()

    # Start the proxy server in its own thread
    proxy_thread = threading.Thread(target=start_proxy)
    proxy_thread.start()