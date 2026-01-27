import socket
import threading
import json
import logging
import time
from shared import config

logging.basicConfig(level=logging.INFO)

class NetworkHandler:
    def __init__(self, host=config.HOST_CLIENT_CONNECT, port=config.PORT_SIGNALING):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.callback = None
        self.receive_thread = None
        self.connected = False
        self.audio_handler = None  # để xử lý AUDIO_DATA
        self.keep_alive_timer = None  # Theo dõi timer keep-alive

    def connect(self, username):
        """Kết nối đến signaling server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(config.SOCKET_TIMEOUT)
            self.sock.connect((self.host, self.port))
            
            # Gửi thông tin đăng ký (thêm \n để phân tách JSON)
            register_msg = {
                'type': 'REGISTER',
                'username': username
            }
            self.sock.sendall((json.dumps(register_msg) + "\n").encode(config.ENCODING))
            
            # Nhận phản hồi với timeout
            self.sock.settimeout(5.0)
            response = self.sock.recv(config.BUFFER_SIZE)
            
            if not response:
                return False, "No response from server"
                
            # chỉ lấy dòng JSON đầu tiên
            lines = response.decode(config.ENCODING).split("\n")
            for line in lines:
                line = line.strip()
                if line:
                    try:
                        response_data = json.loads(line)
                        if response_data.get('type') == 'REGISTER_SUCCESS':
                            self.running = True
                            self.connected = True
                            self.sock.settimeout(None)
                            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                            self.receive_thread.start()

                            # Bắt đầu gửi PING định kỳ
                            self._start_keep_alive()

                            logging.info("[NetworkHandler] Successfully connected to server")
                            return True, "Connected successfully"
                    except json.JSONDecodeError:
                        continue
            
            return False, "Invalid response from server"
                
        except socket.timeout:
            return False, "Connection timeout - server not responding"
        except ConnectionRefusedError:
            return False, "Cannot connect to server - make sure server is running"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        finally:
            # Đảm bảo luôn đặt lại timeout nếu có lỗi
            if not self.connected and self.sock:
                try:
                    self.sock.close()
                except:
                    pass
                self.sock = None
    
    def set_callback(self, callback):
        """Thiết lập callback cho incoming messages"""
        self.callback = callback

    def set_audio_handler(self, handler):
        """Đăng ký audio handler để phát audio"""
        self.audio_handler = handler
    
    def send_message(self, message):
        """Gửi message đến server"""
        if not self.connected or not self.sock:
            logging.warning("[NetworkHandler] Not connected, cannot send message")
            return False
            
        try:
            # Kiểm tra xem socket còn hợp lệ
            self.sock.getpeername()
        except socket.error:
            logging.warning("[NetworkHandler] Socket is invalid, marking as disconnected")
            self.connected = False
            return False
            
        try:
            message_str = json.dumps(message) + "\n"   # Thêm \n ở cuối
            total_sent = 0
            encoded_msg = message_str.encode(config.ENCODING)
            while total_sent < len(encoded_msg):
                try:
                    sent = self.sock.send(encoded_msg[total_sent:])
                    if sent == 0:
                        raise RuntimeError("Socket connection broken")
                    total_sent += sent
                except socket.timeout:
                    continue
                except Exception as e:
                    logging.error(f"[NetworkHandler] Send loop error: {e}")
                    return False
            return True
        except Exception as e:
            logging.error(f"[NetworkHandler] Send error: {e}")
            return False
    
    def _receive_loop(self):
        """Vòng lặp nhận message từ server"""
        buffer = ""
        try:
            while self.running:
                try:
                    data = self.sock.recv(config.BUFFER_SIZE)
                    if not data:
                        break

                    # Cập nhật thời gian hoạt động
                    if hasattr(self, 'client_timeouts') and hasattr(self, 'sock'):
                        with threading.Lock():
                            if self.sock in self.client_timeouts:
                                self.client_timeouts[self.sock] = time.time()

                    # Ghép buffer và tách theo delimiter \n
                    buffer += data.decode(config.ENCODING)
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            message = json.loads(line)
                            msg_type = message.get('type')
                            if msg_type == 'AUDIO_DATA' and self.audio_handler:
                                try:
                                    # LUÔN gửi cả message object để audio_handler tự xử lý
                                    self.audio_handler.handle_audio_data(message)
                                except Exception as e:
                                    logging.error(f"[NetworkHandler] Error handling audio: {e}")
                            elif self.callback:
                                self.callback(message)
                        except json.JSONDecodeError as e:
                            logging.warning(f"[NetworkHandler] Invalid JSON received: {e}")
                            continue
                        
                except socket.timeout:
                    continue
                except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
                    logging.info(f"[NetworkHandler] Connection error: {e}")
                    break
                except Exception as e:
                    logging.error(f"[NetworkHandler] Receive error: {e}")
                    break
        
        except Exception as e:
            logging.error(f"[NetworkHandler] Receive loop error: {e}")
        finally:
            self.connected = False
            logging.info("[NetworkHandler] Receive loop ended")

    def _start_keep_alive(self):
        """Gửi ping định kỳ để giữ kết nối"""
        # Dừng timer cũ nếu có
        if self.keep_alive_timer:
            self.keep_alive_timer.cancel()
            
        if self.running and self.connected:
            try:
                success = self.send_message({'type': 'PING'})
                if not success:
                    logging.warning("[NetworkHandler] Failed to send PING")
            except Exception as e:
                logging.error(f"[NetworkHandler] Keep-alive error: {e}")
                self.connected = False
            
            # Chỉ lên lịch cho lần tiếp theo nếu vẫn đang chạy và kết nối
            if self.running and self.connected:
                self.keep_alive_timer = threading.Timer(30, self._start_keep_alive)
                self.keep_alive_timer.daemon = True
                self.keep_alive_timer.start()

    def is_connected(self):
        return self.connected and self.sock is not None
    
    def disconnect(self):
        """Ngắt kết nối một cách an toàn"""
        self.running = False
        self.connected = False
        
        # Dừng timer keep-alive
        if self.keep_alive_timer:
            self.keep_alive_timer.cancel()
            self.keep_alive_timer = None
        
        if self.sock:
            # CHỈ gửi GOODBYE nếu socket có khả năng gửi được
            try:
                # Kiểm tra socket có đang kết nối hợp lệ không
                self.sock.getpeername()  # Sẽ throw lỗi nếu socket không connected
                goodbye_msg = {'type': 'GOODBYE'}
                # Sử dụng send_message để tận dụng cơ chế gửi an toàn
                self.send_message(goodbye_msg)
            except socket.error as e:
                # Socket không connected, không cần gửi GOODBYE
                logging.debug(f"[NetworkHandler] Socket not connected, skip GOODBYE: {e}")
            except Exception as e:
                logging.error(f"[NetworkHandler] Error sending GOODBYE: {e}")
                
            # CHỈ shutdown socket nếu nó đã được kết nối
            try:
                # Kiểm tra lại xem socket có còn valid không trước khi shutdown
                if self.sock.fileno() != -1:
                    self.sock.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                # Đây là lỗi chúng ta MUỐN bắt được!
                # Socket không connected, không cần shutdown - đây là tình huống bình thường
                logging.debug(f"[NetworkHandler] Socket not connected, skip shutdown: {e}")
            except Exception as e:
                logging.error(f"[NetworkHandler] Error shutting down socket: {e}")
                
            # LUÔN LUÔN cố gắng đóng socket
            try:
                self.sock.close()
            except socket.error as e:
                logging.warning(f"[NetworkHandler] Failed to close socket: {e}")
            except Exception as e:
                logging.error(f"[NetworkHandler] Error closing socket: {e}")
            finally:
                self.sock = None
        
        logging.info("[NetworkHandler] Disconnected cleanly")