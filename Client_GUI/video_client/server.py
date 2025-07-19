import socket
import threading
import struct
import random
from collections import defaultdict
import time


class TestVideoServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.active_tokens = set()

        # Тестовые пользователи
        self.users = {
            'admin': 'password',
            'user': '12345',
            'test': 'test'
        }

        # Тестовые видео
        self.videos = {
            1: {
                'segment_amount': 10,
                'segment_length': 10,
                'max_quality': 2,
                'author': "Test Author",
                'title': "Test Video 1",
                'description': "Sample video 1",
                'segments': self._generate_segments(10, 2)
            },
            2: {
                'segment_amount': 15,
                'segment_length': 10,
                'max_quality': 1,
                'author': "Another Author",
                'title': "Demo Video",
                'description': "Demo video description",
                'segments': self._generate_segments(15, 1)
            }
        }
        print(f"Test server initialized on {host}:{port}")

    def _generate_segments(self, count, max_quality):
        """Генерация тестовых сегментов видео - ерунда нормально не работает"""
        segments = defaultdict(dict)
        for seg_id in range(count):
            for quality in range(max_quality + 1):
                # Генерируем случайные данные для сегмента
                segment_size = random.randint(100000, 500000)
                segments[seg_id][quality] = bytes([random.randint(0, 255) for _ in range(segment_size)])
        return segments

    def _pack_video_info(self, video):
        """Упаковка информации о видео в бинарный формат"""
        author_bytes = video['author'].encode('utf-8')
        title_bytes = video['title'].encode('utf-8')
        desc_bytes = video['description'].encode('utf-8')

        data = struct.pack('!IBB',
                           video['segment_amount'],
                           video['segment_length'],
                           video['max_quality'])
        data += struct.pack('!I', len(author_bytes)) + author_bytes
        data += struct.pack('!I', len(title_bytes)) + title_bytes
        data += struct.pack('!I', len(desc_bytes)) + desc_bytes
        return data

    def _handle_login(self, client_socket):
        """Обработка запроса на авторизацию"""
        try:
            # Читаем логин
            username_len = struct.unpack('!I', client_socket.recv(4))[0]
            username = client_socket.recv(username_len).decode('utf-8')

            # Читаем пароль
            password_len = struct.unpack('!I', client_socket.recv(4))[0]
            password = client_socket.recv(password_len).decode('utf-8')

            # Проверяем учетные данные
            if username in self.users and self.users[username] == password:
                # Генерируем токен
                token = f"token_{username}_{int(time.time())}_{random.randint(1000, 9999)}"
                self.active_tokens.add(token)

                # Отправляем успешный ответ
                client_socket.sendall(bytes([0x00]))  # Код успеха
                token_bytes = token.encode('utf-8')
                client_socket.sendall(struct.pack('!I', len(token_bytes)))
                client_socket.sendall(token_bytes)
                print(f"Successful login for user: {username}")
            else:
                # Отправляем ошибку авторизации
                client_socket.sendall(bytes([0x01]))  # Код ошибки
                print(f"Failed login attempt for user: {username}")
        except Exception as e:
            print(f"Login error: {e}")

    def _handle_get_list(self, client_socket):
        """Обработка запроса списка видео"""
        try:
            # Отправляем количество видео
            client_socket.sendall(struct.pack('!I', len(self.videos)))

            # Отправляем информацию о каждом видео
            for video_id, video in self.videos.items():
                # Отправляем ID видео
                client_socket.sendall(struct.pack('!I', video_id))

                # Упаковываем и отправляем информацию о видео
                video_info = self._pack_video_info(video)
                client_socket.sendall(struct.pack('!I', len(video_info)))
                client_socket.sendall(video_info)
        except Exception as e:
            print(f"Error sending video list: {e}")

    def _handle_get_segment(self, client_socket):
        """Обработка запроса сегмента видео"""
        try:
            # Читаем параметры запроса
            video_id = struct.unpack('!I', client_socket.recv(4))[0]
            segment_id = struct.unpack('!I', client_socket.recv(4))[0]
            quality = struct.unpack('!B', client_socket.recv(1))[0]

            # Получаем запрошенный сегмент
            segment_data = self.videos[video_id]['segments'][segment_id].get(quality, b'')

            # Отправляем размер и данные сегмента
            client_socket.sendall(struct.pack('!I', len(segment_data)))
            if segment_data:
                client_socket.sendall(segment_data)
        except Exception as e:
            print(f"Error handling segment request: {e}")

    def _handle_connection(self, client_socket, address):
        """Обработка подключения клиента"""
        print(f"New connection from {address}")
        try:
            while self.running:
                # Читаем команду
                command = client_socket.recv(1)
                if not command:
                    break

                cmd = command[0]

                if cmd == 0x02:  # GET_LIST
                    self._handle_get_list(client_socket)
                elif cmd == 0x03:  # LOGIN
                    self._handle_login(client_socket)
                elif cmd == 0x01:  # GET_CHUNK
                    self._handle_get_segment(client_socket)
                else:
                    print(f"Unsupported command: {cmd}")
                    break

        except ConnectionResetError:
            print(f"Client {address} disconnected")
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()

    def start(self):
        """Запуск сервера"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"Server started on {self.host}:{self.port}")

        try:
            while self.running:
                client_sock, addr = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_sock, addr)
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("Shutting down server...")
        finally:
            self.stop()

    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")


if __name__ == "__main__":
    server = TestVideoServer()
    server.start()