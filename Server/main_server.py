# Server/main_server.py
import signal
import sys
import time
import logging

from .signaling_server import SignalingServer
from shared import config

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

server = None

def signal_handler(sig, frame):
    """Xử lý khi nhấn Ctrl+C hoặc dừng tiến trình"""
    global server
    logging.info("🛑 Received interrupt signal, stopping server gracefully...")
    if server:
        try:
            server.stop()
        except Exception as e:
            logging.error(f"Error stopping server: {e}")
    sys.exit(0)

def main():
    global server
    
    # Khởi động signaling server
    server = SignalingServer(
        host=config.HOST_SERVER_BIND,
        port=config.PORT_SIGNALING
    )

    # Đăng ký signal handler
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Kill process

    logging.info("🚀 Starting Signaling Server...")
    logging.info(f"📡 Server Address: {config.HOST_SERVER_BIND}:{config.PORT_SIGNALING}")
    logging.info("Press Ctrl+C to stop the server")

    # Biến để theo dõi trạng thái server
    server_restart_count = 0
    max_restart_attempts = 5

    while server_restart_count < max_restart_attempts:
        try:
            server.start()
            
        except KeyboardInterrupt:
            logging.info("Server stopped by user request")
            break
            
        except Exception as e:
            server_restart_count += 1
            logging.error(f"❌ Server crashed: {e}")
            logging.error(f"Traceback: {sys.exc_info()[2]}")
            
            if server_restart_count < max_restart_attempts:
                wait_time = 2 ** server_restart_count  # Exponential backoff
                logging.info(f"🔄 Attempting restart {server_restart_count}/{max_restart_attempts} in {wait_time} seconds...")
                time.sleep(wait_time)
                
                # Tạo lại server instance
                try:
                    server.stop()
                except:
                    pass
                    
                server = SignalingServer(
                    host=config.HOST_SERVER_BIND,
                    port=config.PORT_SIGNALING
                )
            else:
                logging.error("🚨 Maximum restart attempts reached. Server stopped.")
                break
        else:
            # Server stopped normally (không phải do crash)
            break

    # Dọn dẹp trước khi thoát
    try:
        server.stop()
    except Exception as e:
        logging.error(f"Error during final cleanup: {e}")
    
    logging.info("👋 Server shutdown complete")

def health_check():
    """Hàm kiểm tra sức khỏe server (có thể mở rộng)"""
    if server and hasattr(server, 'is_running'):
        return server.is_running()
    return False

if __name__ == "__main__":
    main()