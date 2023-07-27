import os
import socket
import requests
import time
import threading
import argparse



# Function to read the config file manually
def read_config(config_file):
    config = {
        'CACHE_DIR': '',
        'ACCESS_LIMIT': 0,
        'ACCESS_PERIOD': 0,
        'SERVER_IP': '',
        'SERVER_PORT': 0,
        'CACHE_TIME': 0,
        'WHITELISTING': [],
        'TIME_START': 0,
        'TIME_END': 0
    }
    with open(config_file, 'r') as f:
        for line in f:
            key, value = line.strip().split('=')
            key = key.strip()
            value = value.strip()

            if key == 'CACHE_DIR':
                config['CACHE_DIR'] = value
            elif key == 'ACCESS_LIMIT':
                config['ACCESS_LIMIT'] = int(value)
            elif key == 'ACCESS_PERIOD':
                config['ACCESS_PERIOD'] = int(value)
            elif key == 'SERVER_IP':
                config['SERVER_IP'] = value
            elif key == 'SERVER_PORT':
                config['SERVER_PORT'] = int(value)
            elif key == 'CACHE_TIME':
                config['CACHE_TIME'] = int(value)
            elif key == 'WHITELISTING':
                config['WHITELISTING'] = [domain.strip() for domain in value.split(',')]
            elif key == 'TIME':
                time_range = value.split('-')
                config['TIME_START'] = int(time_range[0].strip())
                config['TIME_END'] = int(time_range[1].strip())
    if not all(config.values()):
        raise ValueError("Invalid config file format. Make sure all configuration values are specified.")
    return config

# Kiểm tra xem domain có nằm trong whitelist không
def is_whitelisted(domain, whitelist):
    for i in whitelist:
        if i in domain:
            return True
    return False

# Kiểm tra giới hạn truy cập theo thời gian
def check_access_limit(start_time, end_time):
    current_hour = time.localtime().tm_hour
    return start_time <= current_hour < end_time

# Hàm lưu ảnh vào cache
def save_image_to_cache(url, data, CACHE_DIR):
    filename = os.path.join(CACHE_DIR, url.replace('/', '_').replace(':', '_'))
    with open(filename, 'wb') as f:
        f.write(data)

# Hàm lấy dữ liệu ảnh từ cache
def get_image_from_cache(url, CACHE_DIR):
    filename = os.path.join(CACHE_DIR, url.replace('/', '_').replace(':', '_'))
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return f.read()
    return None

# Biến lưu trữ logs truy cập
access_logs = {}

# Kiểm tra xem URL có phải là một hình ảnh không
def is_image(url):
    return any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp'])

def proxy_thread(client_socket, config):
    CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, TIME_START, TIME_END = config
    request_data = client_socket.recv(4096)
    request_string = request_data.decode('utf-8')

    # Split the request into lines and extract the request line
    request_lines = request_string.strip().split('\r\n')
    request_line = request_lines[0]
    # Extract method and URL from the request line
    method, url, _ = request_line.split(' ')
    start_idx = url.find("://") + len("://")
    end_idx = url.find("/", start_idx)
    url = url[start_idx:end_idx] + url[end_idx:]
    if url.endswith('/'):
        url = url[:-1]
        
    # Kiểm tra phương thức
    if method not in ['GET', 'POST', 'HEAD']:
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed'
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return

    # Kiểm tra giới hạn truy cập theo thời gian
    if not check_access_limit(TIME_START, TIME_END):
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nAccess is limited from {} to {}'.format(TIME_START, TIME_END)
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return

    if not is_whitelisted(url, WHITELISTING):
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden'
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return

    if is_image(url):
        cached_data = get_image_from_cache(url)
        if cached_data:
            response = 'HTTP/1.1 200 OK\r\n\r\n'
            client_socket.sendall(response.encode('utf-8'))
            client_socket.sendall(cached_data)
            client_socket.close()
            return

    headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}

    headers.pop('Host', None)
    response = requests.request(method, f"http://{url}", headers=headers, stream=True)

    if is_image(url) and response.status_code == 200:
        save_image_to_cache(url, response.content)

    for key, value in response.headers.items():
        client_socket.send(f"{key}: {value}\r\n".encode('utf-8'))

    client_socket.send(b'\r\n')

    for chunk in response.iter_content(chunk_size=4096):
        client_socket.send(chunk)

    client_socket.close()


def main(config_file):
    config = read_config(config_file)
    CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, TIME_START, TIME_END  = config
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER_IP, SERVER_PORT))
    server.listen(ACCESS_LIMIT)

    print('Proxy server is listening on port 8888...')
    
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

