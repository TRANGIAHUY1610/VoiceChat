import socket
import threading
import json
import logging
import base64
import time
from shared import config

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")

class SignalingServer:
    def __init__(self, host=config.HOST_SERVER_BIND, port=config.PORT_SIGNALING):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        
        # Quản lý clients và rooms
        self.clients = {}  # sock -> {'username': '', 'room': ''}
        self.rooms = {}    # room_id -> {'sockets': [], 'password': '', 'users': []}
        self.lock = threading.Lock()
        
        # Client timeout management
        self.client_timeouts = {}  # sock -> last activity time

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        
        # Bắt đầu thread quản lý timeout
        timeout_thread = threading.Thread(target=self._check_timeouts, daemon=True)
        timeout_thread.start()
        
        logging.info(f"[SignalingServer] Listening on {self.host}:{self.port}")
        logging.info(f"[SignalingServer] Clients will connect to: {config.HOST_CLIENT_CONNECT}:{config.PORT_SIGNALING}")
        
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(config.SOCKET_TIMEOUT)
                logging.info(f"[SignalingServer] New connection from {addr}")
                
                # Lưu thời gian kết nối
                with self.lock:
                    self.client_timeouts[client_socket] = time.time()
                
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except Exception as e:
                if self.running:
                    logging.error(f"[SignalingServer] Accept error: {e}")

    def _check_timeouts(self):
        """Kiểm tra timeout của clients"""
        while self.running:
            try:
                time.sleep(30)
                current_time = time.time()
                clients_to_remove = []
                
                with self.lock:
                    for sock, last_activity in list(self.client_timeouts.items()):
                        if current_time - last_activity > 120:  # 2 phút không hoạt động
                            clients_to_remove.append(sock)
                    
                    for sock in clients_to_remove:
                        logging.info(f"[SignalingServer] Client timeout, removing")
                        self.remove_client(sock)
                        
            except Exception as e:
                logging.error(f"[SignalingServer] Timeout check error: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logging.info("[SignalingServer] Stopped")

    def handle_client(self, sock):
        buffer = ""
        try:
            while self.running:
                try:
                    data = sock.recv(config.BUFFER_SIZE)
                    if not data:
                        break

                    # Cập nhật thời gian hoạt động
                    with self.lock:
                        self.client_timeouts[sock] = time.time()

                    # Ghép buffer và tách theo delimiter \n
                    buffer += data.decode(config.ENCODING)
                    lines = buffer.split("\n")
                    
                    # Giữ lại phần chưa xử lý cho lần sau
                    buffer = lines.pop() if lines else ""
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            message = json.loads(line)
                            logging.info(f"[ServerDebug] Received: {message.get('type')} from socket {sock.fileno()}")
                            self.process_message(sock, message)
                        except json.JSONDecodeError as e:
                            logging.warning(f"[SignalingServer] Invalid JSON: {e}, data: {line}")
                            continue

                except socket.timeout:
                    continue

        except Exception as e:
            logging.error(f"[SignalingServer] Client error: {e}")
        finally:
            self.remove_client(sock)

    def process_message(self, sock, message):
        """Xử lý message từ client"""
        msg_type = message.get('type')
        with self.lock:
            client_info = self.clients.get(sock, {'username': None, 'room': None})

        if msg_type == 'REGISTER':
            username = message.get('username')
            logging.info(f"[ServerDebug] REGISTER attempt: {username}")
            
            if username and username not in [info['username'] for info in self.clients.values() if info]:
                self.clients[sock] = {'username': username, 'room': None}
                self.send_response(sock, {'type': 'REGISTER_SUCCESS'})
                logging.info(f"[SignalingServer] Registered user: {username}")
            else:
                self.send_response(sock, {'type': 'REGISTER_FAIL', 'message': 'Username already taken or invalid'})
                logging.warning(f"[SignalingServer] Registration failed for: {username}")

        elif msg_type == 'CREATE_ROOM':
            if not client_info['room']:
                room_id = f"room_{int(time.time())}_{len(self.rooms)}"
                password = message.get('password', '')
                self.rooms[room_id] = {'sockets': [sock], 'password': password, 'users': [client_info['username']]}
                self.clients[sock]['room'] = room_id
                self.send_response(sock, {'type': 'ROOM_CREATED', 'room_id': room_id})
                logging.info(f"[SignalingServer] Created room {room_id} by {client_info['username']}")
                logging.info(f"[ServerDebug] Room {room_id} users: {self.rooms[room_id]['users']}")
            else:
                self.send_response(sock, {'type': 'ERROR', 'message': 'Already in a room'})
                logging.warning(f"[ServerDebug] User {client_info['username']} already in room {client_info['room']}")

        elif msg_type == 'JOIN_ROOM':
            room_id = message.get('room_id')
            password = message.get('password', '')
            logging.info(f"[ServerDebug] JOIN_ROOM attempt: {client_info['username']} -> {room_id}")
            
            if room_id in self.rooms and self.rooms[room_id]['password'] == password:
                if client_info['room'] is None:
                    self.rooms[room_id]['sockets'].append(sock)
                    self.rooms[room_id]['users'].append(client_info['username'])
                    self.clients[sock]['room'] = room_id
                    
                    # Gửi phản hồi cho client vừa join
                    self.send_response(sock, {
                        'type': 'JOIN_SUCCESS',
                        'room_id': room_id,
                        'users': self.rooms[room_id]['users']
                    })
                    
                    # Thông báo cho các user khác
                    for client_sock in list(self.rooms[room_id]['sockets']):
                        if client_sock != sock:
                            self.send_response(client_sock, {
                                'type': 'USER_JOINED',
                                'room_id': room_id,
                                'username': client_info['username'],
                                'users': self.rooms[room_id]['users']
                            })
                    
                    logging.info(f"[SignalingServer] {client_info['username']} joined room {room_id}")
                    logging.info(f"[ServerDebug] Room {room_id} now has users: {self.rooms[room_id]['users']}")
                else:
                    self.send_response(sock, {'type': 'ERROR', 'message': 'Already in a room'})
                    logging.warning(f"[ServerDebug] User {client_info['username']} already in room {client_info['room']}")
            else:
                self.send_response(sock, {'type': 'ERROR', 'message': 'Invalid room ID or password'})
                logging.warning(f"[ServerDebug] Join failed: invalid room {room_id} or password")

        elif msg_type == 'AUDIO_DATA':
            with self.lock:
                client_info = self.clients.get(sock)
                if client_info and client_info['room']:
                    room_id = client_info['room']
                    room = self.rooms.get(room_id)
                    if room:
                        # DEBUG QUAN TRỌNG: Log audio data info
                        username = client_info['username']
                        data_size = len(message.get('data', ''))
                        recipient_count = len(room['sockets']) - 1
                        
                        logging.info(f"[AudioDebug] {username} -> Room {room_id}: {data_size} bytes to {recipient_count} recipients")
                        
                        payload = {
                            'type': 'AUDIO_DATA',
                            'from': username
                        }
                        
                        data = message.get('data', '')
                        if data and isinstance(data, str):
                            payload['data'] = data
                            
                            # Forward đến tất cả clients khác trong room
                            forwarded_count = 0
                            for client_sock in list(room['sockets']):
                                if client_sock != sock:
                                    try:
                                        target_user = self.clients.get(client_sock, {}).get('username', 'unknown')
                                        logging.info(f"[AudioDebug] Forwarding to {target_user}")
                                        self.send_response(client_sock, payload)
                                        forwarded_count += 1
                                    except Exception as e:
                                        logging.error(f"[SignalingServer] Error forwarding audio to {target_user}: {e}")
                                        self.remove_client(client_sock)
                            
                            logging.info(f"[AudioDebug] Successfully forwarded to {forwarded_count}/{recipient_count} clients")
                        else:
                            logging.warning(f"[AudioDebug] Invalid audio data from {username}: type={type(data)}, size={data_size}")
                else:
                    logging.warning(f"[AudioDebug] Client not in room, cannot forward audio")

        elif msg_type == 'LEAVE_ROOM':
            self._handle_leave_room(sock)

        elif msg_type == 'GOODBYE':
            logging.info(f"[ServerDebug] GOODBYE from {client_info.get('username', 'unknown')}")
            self.remove_client(sock)

        elif msg_type == 'PING':
            self.send_response(sock, {'type': 'PONG'})
            logging.debug(f"[ServerDebug] PING from {client_info.get('username', 'unknown')}")

        else:
            logging.warning(f"[ServerDebug] Unknown message type: {msg_type}")

    def _handle_leave_room(self, sock):
        """Xử lý client rời phòng"""
        with self.lock:
            client_info = self.clients.get(sock)
            if not client_info or not client_info['room']:
                logging.debug(f"[ServerDebug] LEAVE_ROOM: Client not in any room")
                return
            
            room_id = client_info['room']
            room = self.rooms.get(room_id)
            if room and sock in room['sockets']:
                username = client_info['username']
                room['sockets'].remove(sock)
                if username in room['users']:
                    room['users'].remove(username)
                
                logging.info(f"[ServerDebug] {username} left room {room_id}")
                logging.info(f"[ServerDebug] Room {room_id} remaining users: {room['users']}")
                
                for client_sock in list(room['sockets']):
                    self.send_response(client_sock, {
                        'type': 'USER_LEFT',
                        'room_id': room_id,
                        'username': username,
                        'users': room['users']
                    })
                
                if not room['sockets']:
                    del self.rooms[room_id]
                    logging.info(f"[ServerDebug] Room {room_id} deleted (empty)")
                
                self.clients[sock]['room'] = None

    def send_response(self, sock, message):
        """Gửi response đến client (thêm delimiter \\n)"""
        try:
            message_str = json.dumps(message) + "\n"
            sock.sendall(message_str.encode(config.ENCODING))
            logging.debug(f"[ServerDebug] Sent: {message.get('type')} to socket {sock.fileno()}")
        except Exception as e:
            logging.error(f"[SignalingServer] Send error: {e}")
            self.remove_client(sock)

    def remove_client(self, sock):
        """Xóa client khỏi hệ thống"""
        with self.lock:
            username = self.clients.get(sock, {}).get('username', 'unknown')
            room_id = self.clients.get(sock, {}).get('room')
            
            self._handle_leave_room(sock)
            self.clients.pop(sock, None)
            self.client_timeouts.pop(sock, None)
            
            logging.info(f"[SignalingServer] Removed client: {username} (room: {room_id})")
        
        try:
            sock.close()
        except Exception:
            pass