import os
import socket
import time
import threading
import argparse

# Function to read the config file manually
def read_config(config_file):
    CACHE_DIR = None
    ACCESS_LIMIT = None
    SERVER_IP = None
    SERVER_PORT = None
    CACHE_TIME = None
    WHITELISTING = []
    time_range = None

    with open(config_file, 'r') as f:
        for line in f:
            if 'CACHE_DIR' in line:
                CACHE_DIR = line.split('=')[1].strip()
                if not os.path.exists(CACHE_DIR):
                    os.makedirs(CACHE_DIR)
            elif 'ACCESS_LIMIT' in line:
                ACCESS_LIMIT = int(line.split('=')[1].strip())
            elif 'SERVER_IP' in line:
                SERVER_IP = line.split('=')[1].strip()
            elif 'SERVER_PORT' in line:
                SERVER_PORT = int(line.split('=')[1].strip())
            elif 'CACHE_TIME' in line:
                CACHE_TIME = int(line.split('=')[1].strip())
            elif 'WHITELISTING' in line:
                WHITELISTING = [domain.strip() for domain in line.split('=')[1].split(',')]
            elif 'TIME' in line:
                time_range = line.split('=')[1].strip()

    if any(val is None for val in [CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, time_range]):
        raise ValueError("Invalid config file format. Make sure all required parameters are specified.")
    
    # Split the time range into start and end times
    start_time_str, end_time_str = time_range.split('-')
    start_time = time.strptime(start_time_str, "%H:%M:%S")
    end_time = time.strptime(end_time_str, "%H:%M:%S")

    return CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, start_time, end_time

# Kiểm tra https
def is_https(request_string):
    if ("CONNECT" in request_string):
        return True
    return False

# Kiểm tra xem domain có nằm trong whitelist không
def is_whitelisted(domain, whitelist):
    for i in whitelist:
        if i in domain:
            return True
    return False

def response403():
    with open("custom403.html", "rb") as html_file:
        content = html_file.read()
        response = b"HTTP/1.0 403 Forbidden\r\nContent-Type: text/html\r\n\r\n" + content
    return response

# Kiểm tra giới hạn truy cập theo thời gian
def check_ACCESS_LIMIT(start_time, end_time):
    current_time = time.localtime()
    CURRENT_TIME = current_time.tm_hour * 3600 + current_time.tm_min * 60 + current_time.tm_sec
    START_TIME = start_time.tm_hour * 3600 + start_time.tm_min * 60 + start_time.tm_sec
    END_TIME = end_time.tm_hour * 3600 + end_time.tm_min * 60 + end_time.tm_sec
    return START_TIME <= CURRENT_TIME <= END_TIME

# Kiểm tra xem cache đã hết hạn chưa
def is_cache_expired(filename, CACHE_TIME):
    current_time = time.time()
    file_mtime = os.path.getmtime(filename)
    cache_age = current_time - file_mtime
    return cache_age > CACHE_TIME

# Hàm lưu ảnh vào cache và ghi lại thời điểm lưu cache
def save_image_to_cache(url, data, CACHE_DIR):
    filename = os.path.join(CACHE_DIR, url.replace('/', '_').replace(':', '_'))
    with open(filename, 'wb') as f:
        f.write(data)
    with open(filename + '.time', 'w') as f_time:
        f_time.write(str(time.time()))

# Hàm lấy dữ liệu ảnh từ cache và kiểm tra thời gian cache
def get_image_from_cache(url, CACHE_DIR, CACHE_TIME):
    filename = os.path.join(CACHE_DIR, url.replace('/', '_').replace(':', '_'))
    cache_time_filename = filename + '.time'
    if os.path.exists(filename) and os.path.exists(cache_time_filename):
        if not is_cache_expired(cache_time_filename, CACHE_TIME):
            with open(filename, 'rb') as f:
                return f.read()
        else:
            # Xóa cache và cache time nếu đã hết hạn
            os.remove(filename)
            os.remove(cache_time_filename)
    return None

# Luồng thực hiện việc loại bỏ các đối tượng đã hết hạn khỏi cache sau mỗi 15 phút
def remove_expired_cache(CACHE_DIR, CACHE_TIME):
    while True:
        time.sleep(CACHE_TIME) 
        current_time = time.time()
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith('.time'):
                cache_time_filename = os.path.join(CACHE_DIR, filename)
                with open(cache_time_filename, 'r') as f_time:
                    cache_time = float(f_time.read())
                cache_age = current_time - cache_time
                if cache_age > CACHE_TIME:
                    # Xóa cache và cache time nếu đã hết hạn
                    cache_filename = os.path.join(CACHE_DIR, filename[:-5])
                    os.remove(cache_filename)
                    os.remove(cache_time_filename)

# Biến lưu trữ logs truy cập
access_logs = {}

# Kiểm tra xem URL có phải là một hình ảnh không
def is_image(url):
    return any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp'])


# Xử lí chuỗi request
def handle_request(request_data):
    try:
        line = request_data.decode()
        method = line.split(' ')[0]
        url = line.split(' ')[1]
        host_name = url.split('/')[2]
        return method, url, host_name
    except:
        return None, None, None

def create_http_request(method, url, headers):
    headers_str = '\r\n'.join(f"{key}: {value}" for key, value in headers.items())
    request_str = f"{method} / HTTP/1.1\r\nHost: {url}\r\n{headers_str}\r\n\r\n"
    return request_str.encode('utf-8')

def get_status(server_respone):
    buf = server_respone.split(b'\r\n')[0]
    return buf.split(b' ')[1]

def get_connection_close(server_respone):
    return "connection: close" in server_respone.decode().lower()

def get_content_length(headers):
    line = headers.split(b"\r\n")
    for l in line:
        if l.startswith(b"Content-Length:") or l.startswith(b"content-length"):
            length = int(l.split(b":")[1].strip())
            return length
    return 0

def get_server_respone(host_name, request_data):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((host_name, 80))
    server_socket.sendall(request_data)
    
    # Get the response from web server
    server_respone = server_socket.recv(4096)

    # Get the header of the request
    chunked_encoding = False
    header_end = server_respone.find(b"\r\n\r\n")
    headers = server_respone[:header_end]
    
    # If the response is error code, return 403 Forbidden
    if get_status(server_respone) in [400, 401, 403, 404]:
        return response403()
    
    # If the response is "connection: close", get the response until the end of the response (the web server will closed eventually)
    if get_connection_close(headers):
        while True:
            data_chunk = server_socket.recv(4096)
            if (data_chunk):
                server_respone += data_chunk
            else:
                return server_respone

    # If the response is not "connection: close" and the body part is not empty, get the response by following the content length or chunked encoding
    if header_end + 4 != len(server_respone):    
        chunked_encoding = "transfer-encoding: chunked" in headers.decode().lower()
        content_length = get_content_length(headers)
        # If the response is not chunked encoding, get the response by content length
        if not chunked_encoding and content_length > 0:
            if len(server_respone) < header_end + 4 + content_length:
                length = content_length - (len(server_respone) - header_end - 4)
                while len(server_respone) < header_end + content_length + 4:
                    server_respone += server_socket.recv(length)
        else:  # If the response is chunked encoding, get the response until meet '0' in the body part
            end_check = b'0'
            chunked_part = server_respone.split(b"\r\n\r\n")[1]
            chunks = chunked_part.split(b"\r\n")
            if end_check not in chunks:
                while True:
                    data_chunk = server_socket.recv(4096)
                    server_respone += data_chunk
                    data_chunks = data_chunk.split(b"\r\n")
                    if end_check in data_chunks:
                        break
    
    server_socket.close()
    return server_respone

def proxy_thread(client_socket, config):
    try:
        CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config
        request_data = client_socket.recv(4096)
        method, url, host_name = handle_request(request_data)
        request_lines = request_data.decode().strip().split('\r\n')

        print(request_data.decode())
        if len(request_lines) > 0:
            print("========================================================================================")

        if method not in ['GET', 'POST', 'HEAD'] or not check_ACCESS_LIMIT(START_TIME, END_TIME) or not is_whitelisted(url, WHITELISTING):
            client_socket.sendall(response403())
            client_socket.close()
            return

        # if method == 'POST':
        #     client_socket.sendall(request_data.encode('utf-8'))
        # else:
        #     remote_request = f"{method} {url} HTTP/1.1\r\nHost: {host_name}\r\n\r\n".encode()
        #     client_socket.sendall(remote_request)

        if is_image(url):
            cached_data = get_image_from_cache(url, CACHE_DIR, CACHE_TIME)
            if cached_data:
                response = 'HTTP/1.1 200 OK\r\n\r\n'
                client_socket.sendall(response.encode('utf-8'))
                client_socket.sendall(cached_data)
                client_socket.close()
                return

        server_response = get_server_respone(host_name, request_data)
        client_socket.sendall(server_response)
        client_socket.close()

    except OSError:
        client_socket.close()


def main(config_file):
    config = read_config(config_file)
    CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Bắt đầu luồng loại bỏ cache hết hạn
    remove_cache_thread = threading.Thread(target=remove_expired_cache, args=(CACHE_DIR, CACHE_TIME))
    remove_cache_thread.daemon = True
    remove_cache_thread.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(ACCESS_LIMIT)

    print('Proxy server ' + SERVER_IP + ' is listening on port ' + str(SERVER_PORT) + '...')
    
    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_thread = threading.Thread(target=proxy_thread, args=(client_socket, config))
        client_thread.start()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Proxy Server with Config File')
    parser.add_argument('config', help='Path to the config file')
    args = parser.parse_args()
    main(args.config)
