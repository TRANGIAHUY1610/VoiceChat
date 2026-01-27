# shared/config.py
# Cấu hình dùng chung cho client & server

HOST_SERVER_BIND = "10.63.92.158"
HOST_CLIENT_CONNECT = "10.63.92.158"

PORT_AUDIO = 5002
PORT_SIGNALING = 5001

BUFFER_SIZE = 4096
ENCODING = "utf-8"

#  GIẢM CHUNK SIZE để giảm độ trễ
AUDIO_CHUNK = 256      # Giảm từ 1024 xuống 256 (giảm 4 lần)
AUDIO_RATE = 16000     # Giảm từ 44100 xuống 16000 (đủ cho voice)
AUDIO_CHANNELS = 1
AUDIO_FORMAT = 2       # pyaudio.paInt16

# Socket/timeouts
SOCKET_TIMEOUT = 5.0
CONNECTION_TIMEOUT = 10.0

#  Thêm cấu hình mới cho audio processing
AUDIO_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
SILENCE_THRESHOLD = 100  # Ngưỡng silence detection