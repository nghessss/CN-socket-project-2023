from socket import *
import sys
import threading
import os
import time

# Whitelisted websites
whitelist = ["example.com", "example2.com"]  # Add allowed websites here

# Cache directory for storing images
cache_directory = "cache"
if not os.path.exists(cache_directory):
    os.makedirs(cache_directory)

# Set caching time for images (in seconds)
cache_time = 60 * 60  # 1 hour

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
    if not is_whitelisted(host):
        # Return 403 Forbidden with custom HTML content
        # response = b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/html\r\n\r\n"
        # response += b"<html><body><h1>403 Forbidden</h1>"
        # response += b"<p>You are not allowed to access this website.</p>"
        # response += b"</body></html>"
        # Return 403 Forbidden with custom HTML content
        response = b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/html\r\n\r\n"
        response += b"<!DOCTYPE html>\n<html lang='en'>\n<head>\n<meta charset='UTF-8'>\n<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n<title>403 Error</title>\n<style>\n"
        # Append the custom CSS styles here
        response += b"""body {
                          background: #1b1b1b;
                          color: white;
                          font-family: "Bungee", cursive;
                          margin-top: 50px;
                          text-align: center;
                        }
                        
                        a {
                          color: #2aa7cc;
                          text-decoration: none;
                        }
                        
                        a:hover {
                          color: white;
                        }
                        
                        svg {
                          width: 50vw;
                        }
                        
                        .lightblue {
                          fill: #444;
                        }
                        
                        .eye {
                          cx: calc(115px + 30px * var(--mouse-x));
                          cy: calc(50px + 30px * var(--mouse-y));
                        }
                        
                        #eye-wrap {
                          overflow: hidden;
                        }
                        
                        .error-text {
                          font-size: 120px;
                        }
                        
                        .alarm {
                          animation: alarmOn 0.5s infinite;
                        }
                        
                        @keyframes alarmOn {
                          to {
                            fill: darkred;
                          }
                        }</style>\n</head>\n<body>\n<svg xmlns='http://www.w3.org/2000/svg' id='robot-error' viewBox='0 0 260 118.9' role='img'>\n<title xml:lang='en'>403 Error</title>\n<defs>\n<clipPath id='white-clip'>\n<circle id='white-eye' fill='#cacaca' cx='130' cy='65' r='20' />\n</clipPath>\n<text id='text-s' class='error-text' y='106'> 403 </text>\n</defs>\n<path class='alarm' fill='#e62326' d='M120.9 19.6V9.1c0-5 4.1-9.1 9.1-9.1h0c5 0 9.1 4.1 9.1 9.1v10.6' />\n<use xlink:href='#text-s' x='-0.5px' y='-1px' fill='black'></use>\n<use xlink:href='#text-s' fill='#2b2b2b'></use>\n<g id='robot'>\n<g id='eye-wrap'>\n<use xlink:href='#white-eye'></use>\n<circle id='eyef' class='eye' clip-path='url(#white-clip)' fill='#000' stroke='#2aa7cc' stroke-width='2' stroke-miterlimit='10' cx='130' cy='65' r='11' />\n<ellipse id='white-eye' fill='#2b2b2b' cx='130' cy='40' rx='18' ry='12' />\n</g>\n<circle class='lightblue' cx='105' cy='32' r='2.5' id='tornillo' />\n<use xlink:href='#tornillo' x='50'></use>\n<use xlink:href='#tornillo' x='50' y='60'></use>\n<use xlink:href='#tornillo' y='60'></use>\n</g>\n</svg>\n<h1>You are not allowed to enter here</h1>\n<script>\nvar root = document.documentElement;\nvar eyef = document.getElementById('eyef');\nvar cx = document.getElementById('eyef').getAttribute('cx');\nvar cy = document.getElementById('eyef').getAttribute('cy');\ndocument.addEventListener('mousemove', evt => {\nlet x = evt.clientX / innerWidth;\nlet y = evt.clientY / innerHeight;\nroot.style.setProperty('--mouse-x', x);\nroot.style.setProperty('--mouse-y', y);\ncx = 115 + 30 * x;\ncy = 50 + 30 * y;\neyef.setAttribute('cx', cx);\neyef.setAttribute('cy', cy);\n});\ndocument.addEventListener('touchmove', touchHandler => {\nlet x = touchHandler.touches[0].clientX / innerWidth;\nlet y = touchHandler.touches[0].clientY / innerHeight;\nroot.style.setProperty('--mouse-x', x);\nroot.style.setProperty('--mouse-y', y);\n});\n</script>\n</body>\n</html>\n"""
        # End of custom CSS styles
        response += b"</body></html>"
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
