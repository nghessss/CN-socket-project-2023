import os
import socket
import requests
import time
import threading
import argparse
import gzip

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
def handle_request(request_string):
    request_lines = request_string.strip().split('\r\n')
    request_line = request_lines[0]
    method, url, _ = request_line.split(' ')
    start_idx = url.find("://") + len("://")
    end_idx = url.find("/", start_idx)
    url = url[start_idx:end_idx] + url[end_idx:]
    if url.endswith('/'):
        url = url[:-1]
    return  request_line, request_lines, method, url, _


def proxy_thread(client_socket, config):
    CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config
    request_data = client_socket.recv(4096)
    request_string = request_data.decode('utf-8')
    print(request_string)
    print("========================================================================================")
    request_line, request_lines, method, url, _ = handle_request(request_string)
    # Kiểm tra phương thức
    if method not in ['GET', 'POST', 'HEAD']:
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed'
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return

    # Kiểm tra giới hạn truy cập theo thời gian
    if not check_ACCESS_LIMIT(START_TIME, END_TIME):
        start_time_str = time.strftime('%H:%M:%S', START_TIME)
        end_time_str = time.strftime('%H:%M:%S', END_TIME)
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nAccess is limited from {} to {}'.format(start_time_str, end_time_str)
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return
    # Kiểm tra có nằm trong whitelist không
    if not is_whitelisted(url, WHITELISTING):
        response = 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden'
        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        return
    if is_image(url):
        cached_data = get_image_from_cache(url, CACHE_DIR, CACHE_TIME)
        if cached_data:
            response = 'HTTP/1.1 200 OK\r\n\r\n'
            client_socket.sendall(response.encode('utf-8'))
            client_socket.sendall(cached_data)
            client_socket.close()
            return
        
    headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}

    headers.pop('Host', None)
    response = requests.request(method, f"http://{url}", headers=headers, stream=True)
    # response_status_code
    # response_content
    # response_header
    # response_text
    # response.iter_content(chunk_size=4096):
    # print(response.content.decode('utf-8'))
    
    if is_image(url) and response.status_code == 200:
        save_image_to_cache(url, response.content, CACHE_DIR)
    print(response.content)
    
    print("focus hereeeeeeeee")
    content_type = response.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        response_text = response.text
        headers = f'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n'
        print(headers + "header here\n")
        print(response_text + "response here\n")
        client_socket.sendall(headers.encode('utf-8'))
        client_socket.sendall(response_text.encode('utf-8'))
    else:
        # For other content types, send the binary data directly
        headers = f'HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n'
        client_socket.sendall(headers.encode('utf-8'))
        for chunk in response.iter_content(chunk_size=4096):
            client_socket.send(chunk)

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
