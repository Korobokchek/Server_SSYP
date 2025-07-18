import socket
import struct
from .protocols import VideoInfo, Protocol
from .logger import logger


class NetworkClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.token = None
        logger.info(f"Initializing NetworkClient for {host}:{port}")


    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info("Successfully connected to server")
            return True
        except socket.error as e:
            logger.error(f"Connection failed: {str(e)}")
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
                logger.info("Disconnected from server")
            except socket.error as e:
                logger.error(f"Error while disconnecting: {str(e)}")
            finally:
                self.socket = None

    def _send_all(self, data):
        try:
            self.socket.sendall(data)
            logger.debug(f"Sent {len(data)} bytes")
        except socket.error as e:
            logger.error(f"Failed to send data: {str(e)}")
            raise

    def _recv_all(self, size):
        try:
            data = bytearray()
            while len(data) < size:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise socket.error("Connection closed by server")
                data.extend(packet)
            logger.debug(f"Received {len(data)} bytes")
            return bytes(data)
        except socket.error as e:
            logger.error(f"Failed to receive data: {str(e)}")
            raise

    def login(self, username, password):
        try:
            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')

            data = bytes([Protocol.LOGIN])
            data += struct.pack('!I', len(username_bytes)) + username_bytes
            data += struct.pack('!I', len(password_bytes)) + password_bytes

            self._send_all(data)

            response = self._recv_all(1)[0]

            if response == 0x00:  # Success
                token_len = struct.unpack('!I', self._recv_all(4))[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                return True
            return False
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False

    def get_video_list(self):
        """Получение списка доступных видео"""
        try:
            # Отправляем команду GET_LIST
            self._send_all(bytes([Protocol.GET_LIST]))

            # Получаем количество видео (4 байта)
            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            logger.info(f"Receiving {count} video entries")

            videos = []
            for _ in range(count):
                # Получаем ID видео (4 байта)
                video_id = struct.unpack('!I', self._recv_all(4))[0]

                # Получаем размер данных видео (4 байта)
                info_size = struct.unpack('!I', self._recv_all(4))[0]

                # Получаем данные видео
                video_info_data = self._recv_all(info_size)
                video_info = VideoInfo.from_bytes(video_info_data)

                videos.append((video_id, video_info))
                logger.debug(f"Received video info: ID={video_id}, Title={video_info.title}")

            return videos
        except Exception as e:
            logger.error(f"Failed to get video list: {str(e)}")
            return None

    def get_video_segment(self, video_id, segment_id, quality):
        try:
            data = struct.pack('!BIIB', Protocol.GET_CHUNK, video_id, segment_id, quality)
            self._send_all(data)

            size = struct.unpack('!I', self._recv_all(4))[0]
            return self._recv_all(size)
        except Exception as e:
            logger.error(f"Error getting video segment: {e}")
            return None