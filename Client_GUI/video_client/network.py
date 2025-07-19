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
        logger.info(f"Инициализация NetworkClient для {host}:{port}")

    def is_connected(self):
        return self.socket is not None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info("Успешное подключение к серверу")
            return True
        except socket.error as e:
            logger.error(f"Ошибка подключения: {str(e)}")
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
                logger.info("Отключение от сервера")
            except socket.error as e:
                logger.error(f"Ошибка отключения: {str(e)}")
            finally:
                self.socket = None
                self.token = None

    def _send_all(self, data):
        try:
            self.socket.sendall(data)
            logger.debug(f"Отправлено {len(data)} байт")
        except socket.error as e:
            logger.error(f"Ошибка отправки данных: {str(e)}")
            raise

    def _recv_all(self, size):
        try:
            data = bytearray()
            while len(data) < size:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise socket.error("Сервер закрыл соединение")
                data.extend(packet)
            logger.debug(f"Получено {len(data)} байт")
            return bytes(data)
        except socket.error as e:
            logger.error(f"Ошибка получения данных: {str(e)}")
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

            if response == 0x00:  # Успех
                token_len = struct.unpack('!I', self._recv_all(4))[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                logger.info("Успешная авторизация")
                return True
            logger.warning("Неудачная авторизация")
            return False
        except Exception as e:
            logger.error(f"Ошибка авторизации: {str(e)}")
            return False

    def is_connected(self):
        """Проверка подключения к серверу"""
        return self.socket is not None and hasattr(self.socket, 'fileno')

    def get_video_list(self):
        try:
            self._send_all(bytes([Protocol.GET_LIST]))

            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            logger.info(f"Получение {count} видео")

            videos = []
            for _ in range(count):
                video_id = struct.unpack('!I', self._recv_all(4))[0]
                info_size = struct.unpack('!I', self._recv_all(4))[0]
                video_info_data = self._recv_all(info_size)
                video_info = VideoInfo.from_bytes(video_info_data)

                videos.append((video_id, video_info))
                logger.debug(f"Получена информация о видео: ID={video_id}, Название={video_info.title}")

            return videos
        except Exception as e:
            logger.error(f"Ошибка получения списка видео: {str(e)}")
            return None

    def get_video_segment(self, video_id, segment_id, quality):
        try:
            data = struct.pack('!BIIB', Protocol.GET_CHUNK, video_id, segment_id, quality)
            self._send_all(data)

            size = struct.unpack('!I', self._recv_all(4))[0]
            return self._recv_all(size)
        except Exception as e:
            logger.error(f"Ошибка получения сегмента видео: {e}")
            return None