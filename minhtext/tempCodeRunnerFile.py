# def proxy_thread(client_socket, config):
#     CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config
#     request_data = client_socket.recv(4096)
#     request_string = request_data.decode('utf-8')
    
#     request_line, request_lines, method, url, _ = handle_request(request_string)
    
#     if method not in ['GET', 'POST', 'HEAD']:
#         response = 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed'
#         client_socket.sendall(response.encode('utf-8'))
#         client_socket.close()
#         return
    
#     if not check_access_limit(START_TIME, END_TIME):
#         start_time_str = time.strftime('%H:%M:%S', START_TIME)
#         end_time_str = time.strftime('%H:%M:%S', END_TIME)
#         response = f'HTTP/1.1 403 Forbidden\r\n\r\nAccess is limited from {start_time_str} to {end_time_str}'
#         client_socket.sendall(response.encode('utf-8'))
#         client_socket.close()
#         return
    
#     if not is_whitelisted(url, WHITELISTING):
#         response = 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden'
#         client_socket.sendall(response.encode('utf-8'))
#         client_socket.close()
#         return
    
#     headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}
#     headers.pop('Host', None)

#     if method == 'GET' or method == 'HEAD':
#         response = send_http_request(method, f"http://{url}", headers)
#         response_lines = response.split(b'\r\n\r\n', 1)
#         response_headers = response_lines[0]
#         response_content = response_lines[1] if len(response_lines) > 1 else b'' 
        
#         # Check for "Transfer-Encoding: chunked" and handle accordingly
#         if b'Transfer-Encoding: chunked' in response_headers:
#             chunks = response_content.split(b'\r\n')
#             chunked_data = b"".join(chunks[1:-2])  # Join chunks, excluding the last empty line
#             response_content = chunked_data

#         if is_image(url):
#             cached_data = get_image_from_cache(url, CACHE_DIR, CACHE_TIME)
#             if cached_data:
#                 response = 'HTTP/1.1 200 OK\r\n\r\n'
#                 client_socket.sendall(response.encode('utf-8'))
#                 client_socket.sendall(cached_data)
#                 client_socket.close()
#                 return
        
#         response_data = parse_response(response_headers.decode('utf-8'))
#         response_content_type = response_data['content_type']
#         response_content_encoding = response_data['content_encoding']

#         response_headers = response_headers.decode('utf-8')

#         response_img = response_content
#         # if 'gzip' in response_content_encoding:
#         #     response_img = gzip.decompress(response_img)
#         # elif 'deflate' in response_content_encoding:
#         #     response_img = zlib.decompress(response_img, -zlib.MAX_WBITS)

#         if method == 'GET':
#             if (is_image(url)):
#                 response_img = response_content
#                 # response_img.decode('utf-8')
#                 save_image_to_cache(url, response_img, CACHE_DIR)
#             client_socket.sendall(response_headers.encode('utf-8'))
#             client_socket.sendall(b'\r\n\r\n')
#             client_socket.sendall(response_content)
#         elif method == 'HEAD':
#             client_socket.sendall(response_headers.encode('utf-8'))
#             client_socket.sendall(b'\r\n\r\n')
#     client_socket.close()
# def proxy_thread(client_socket, config):
#     CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config

#     while True:
#         request_data = client_socket.recv(4096)
#         if not request_data:
#             break

#         request_string = request_data.decode('utf-8')
#         request_line, request_lines, method, url, _ = handle_request(request_string)

#         if method not in ['GET', 'POST', 'HEAD']:
#             response = 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed'
#             client_socket.sendall(response.encode('utf-8'))
#             client_socket.close()
#             return

#         if not check_access_limit(START_TIME, END_TIME):
#             start_time_str = time.strftime('%H:%M:%S', START_TIME)
#             end_time_str = time.strftime('%H:%M:%S', END_TIME)
#             response = f'HTTP/1.1 403 Forbidden\r\n\r\nAccess is limited from {start_time_str} to {end_time_str}'
#             client_socket.sendall(response.encode('utf-8'))
#             client_socket.close()
#             return

#         if not is_whitelisted(url, WHITELISTING):
#             response = 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden'
#             client_socket.sendall(response.encode('utf-8'))
#             client_socket.close()
#             return

#         headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}
#         headers.pop('Host', None)

#         if method == 'GET' or method == 'HEAD':
#             response = send_http_request(method, f"http://{url}", headers)
#             response_lines = response.split(b'\r\n\r\n', 1)
#             response_headers = response_lines[0]
#             response_content = response_lines[1] if len(response_lines) > 1 else b''

#             # Check for "Transfer-Encoding: chunked" and handle accordingly
#             if b'Transfer-Encoding: chunked' in response_headers:
#                 chunks = response_content.split(b'\r\n')
#                 chunked_data = b"".join(chunks[1:-2])  # Join chunks, excluding the last empty line
#                 response_content = chunked_data

#             response_data = parse_response(response_headers.decode('utf-8'))
#             response_content_type = response_data['content_type']
#             response_content_encoding = response_data['content_encoding']

#             response_headers = response_headers.decode('utf-8')

#             response_img = response_content
#             # if 'gzip' in response_content_encoding:
#             #     response_img = gzip.decompress(response_img)
#             # elif 'deflate' in response_content_encoding:
#             #     response_img = zlib.decompress(response_img, -zlib.MAX_WBITS)

#             if method == 'GET':
#                 if is_image(url):
#                     response_img = response_content
#                     save_image_to_cache(url, response_img, CACHE_DIR)

#                 # Send headers and content
#                 client_socket.sendall(response_headers.encode('utf-8'))
#                 client_socket.sendall(b'\r\n\r\n')
#                 client_socket.sendall(response_content)

#         # For the Keep-Alive case, do not close the client socket
#         if 'Connection' in headers and headers['Connection'] == 'Keep-Alive':
#             continue
#         else:
#             break  # Exit the loop and close the socket

#     client_socket.close()


# def proxy_thread(client_socket, config):
#     CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config

#     while True:
#         try:
#             request_data = client_socket.recv(4096)
#             if not request_data:
#                 break
            
#             request_string = request_data.decode('utf-8')
#             request_line, request_lines, method, url, _ = handle_request(request_string)
            
#             if method not in ['GET', 'POST', 'HEAD']:
#                 send_response(client_socket, 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed')
#                 break
            
#             if not check_access_limit(START_TIME, END_TIME):
#                 send_response(client_socket, f'HTTP/1.1 403 Forbidden\r\n\r\n')
#                 break
            
#             if not is_whitelisted(url, WHITELISTING):
#                 send_response(client_socket, 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden')
#                 break
            
#             headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}
#             headers.pop('Host', None)
            
#             if method == 'GET' or method == 'HEAD':
#                 response = send_http_request(method, f"http://{url}", headers)
#                 response_lines = response.split(b'\r\n\r\n', 1)
#                 response_headers = response_lines[0]
#                 response_content = response_lines[1] if len(response_lines) > 1 else b''
                
#                 # Check for "Transfer-Encoding: chunked" and handle accordingly
#                 if b'Transfer-Encoding: chunked' in response_headers:
#                     chunks = response_content.split(b'\r\n')
#                     chunked_data = b"".join(chunks[1:-2])  # Join chunks, excluding the last empty line
#                     response_content = chunked_data
                
#                 response_headers = response_headers.decode('utf-8')
                
#                 if method == 'GET':
#                     if is_image(url):
#                         cached_data = get_image_from_cache(url, CACHE_DIR, CACHE_TIME)
#                         if cached_data:
#                             send_response(client_socket, 'HTTP/1.1 200 OK\r\n\r\n', cached_data)
#                             continue  # Keep the connection alive for Keep-Alive requests
#                         else:
#                             save_image_to_cache(url, response_content, CACHE_DIR)
                
#                     send_response(client_socket, response_headers, response_content)
#             elif method == 'POST':
#                 content_length = int(headers.get('Content-Length', 0))
#                 post_data = b""
#                 while len(post_data) < content_length:
#                     chunk = client_socket.recv(min(4096, content_length - len(post_data)))
#                     if not chunk:
#                         break
#                     post_data += chunk

#                 response = send_http_request(method, f"http://{url}", headers, post_data)
#                 response_lines = response.split(b'\r\n\r\n', 1)
#                 response_headers = response_lines[0]
#                 response_content = response_lines[1] if len(response_lines) > 1 else b''

#                 response_headers = response_headers.decode('utf-8')

#                 send_response(client_socket, response_headers, response_content)

#             # For the Keep-Alive case, do not close the client socket
#             if 'Connection' in headers and headers['Connection'] == 'Keep-Alive':
#                 continue
#             else:
#                 break  # Exit the loop and close the socket
        
#         except Exception as e:
#             print("An error occurred:", e)
#             break
    
#     client_socket.close()

# def proxy_thread(client_socket, config):
    CACHE_DIR, ACCESS_LIMIT, SERVER_IP, SERVER_PORT, CACHE_TIME, WHITELISTING, START_TIME, END_TIME = config

    try:
        request_data = client_socket.recv(4096)
        if not request_data:
            return
        
        request_string = request_data.decode('utf-8')
        request_line, request_lines, method, url, _ = handle_request(request_string)
        
        if method not in ['GET', 'POST', 'HEAD']:
            send_response(client_socket, 'HTTP/1.1 403 Forbidden\r\n\r\nMethod Not Allowed')
            client_socket.close()
            return
        
        if not check_access_limit(START_TIME, END_TIME):
            send_response(client_socket, 'HTTP/1.1 403 Forbidden\r\n\r\n')
            client_socket.close()
            return
        
        if not is_whitelisted(url, WHITELISTING):
            send_response(client_socket, 'HTTP/1.1 403 Forbidden\r\n\r\nForbidden')
            client_socket.close()
            return
        
        headers = {line.split(': ')[0]: line.split(': ')[1] for line in request_lines[1:]}
        headers.pop('Host', None)
        
        if method == 'GET' or method == 'HEAD':
            response = send_http_request(method, f"http://{url}", headers)
            response_lines = response.split(b'\r\n\r\n', 1)
            response_headers = response_lines[0]
            response_content = response_lines[1] if len(response_lines) > 1 else b''
            
            # Check for "Transfer-Encoding: chunked" and handle accordingly
            if b'Transfer-Encoding: chunked' in response_headers:
                chunks = response_content.split(b'\r\n')
                chunked_data = b"".join(chunks[1:-2])  # Join chunks, excluding the last empty line
                response_content = chunked_data
            
            response_headers = response_headers.decode('utf-8')
            
            if method == 'GET':
                if is_image(url):
                    cached_data = get_image_from_cache(url, CACHE_DIR, CACHE_TIME)
                    if cached_data:
                        send_response(client_socket, 'HTTP/1.1 200 OK\r\n\r\n', cached_data)
                        client_socket.close()
                        return
                    else:
                        save_image_to_cache(url, response_content, CACHE_DIR)
            
                send_response(client_socket, response_headers, response_content)
        elif method == 'POST':
            content_length = int(headers.get('Content-Length', 0))
            post_data = b""
            while len(post_data) < content_length:
                chunk = client_socket.recv(min(4096, content_length - len(post_data)))
                if not chunk:
                    break
                post_data += chunk

            response = send_http_request(method, f"http://{url}", headers, post_data)
            response_lines = response.split(b'\r\n\r\n', 1)
            response_headers = response_lines[0]
            response_content = response_lines[1] if len(response_lines) > 1 else b''

            response_headers = response_headers.decode('utf-8')

            send_response(client_socket, response_headers, response_content)

        client_socket.close()
        
    except Exception as e:
        print("An error occurred:", e)
        client_socket.close()
