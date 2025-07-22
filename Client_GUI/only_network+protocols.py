import socket
import struct
import sys


class Protocol:
    """Протокол"""
    GET_INFO = 0x00
    GET_CHUNK = 0x01
    GET_LIST = 0x02
    LOGIN = 0x03
    REGISTER = 0x04
    UPLOAD = 0x05
    GET_USER_VIDEOS = 0x06 #сам добавил(нету в протоколе)
    EDIT_VIDEO = 0x07 #сам добавил(нету в протоколе)

    # Ответы авторизации(login)
    LOGIN_SUCCESS = 0x00
    LOGIN_NO_ACCOUNT = 0x01
    LOGIN_WRONG_PASSWORD = 0x02

    # Ответы регистрации(registr)/
    REGISTER_SUCCESS = 0x00
    REGISTER_USERNAME_TAKEN = 0x01
    REGISTER_INVALID_CREDENTIALS = 0x02

    # Ответы загрузки
    UPLOAD_PROGRESS = 0x00
    UPLOAD_FAILURE = 0x01
    UPLOAD_SUCCESS = 0x02

    @staticmethod
    def command_to_str(cmd):
        commands = {
            GET_INFO: 'GET_INFO',
            GET_CHUNK: 'GET_CHUNK',
            GET_LIST: 'GET_LIST',
            LOGIN: 'LOGIN',
            REGISTER: 'REGISTER',
            UPLOAD: 'UPLOAD',
            GET_USER_VIDEOS: 'GET_USER_VIDEOS',
            EDIT_VIDEO: 'EDIT_VIDEO'
        }
        return commands.get(cmd, 'UNKNOWN')


class NetworkTester:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.token = None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Connected to server successfully")
            return True
        except socket.error as e:
            print(f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
                print("Disconnected from server")
            except socket.error as e:
                print(f"Disconnection error: {str(e)}")
            finally:
                self.socket = None
                self.token = None

    def _send_all(self, data):
        try:
            self.socket.sendall(data)
            print(f"Sent {len(data)} bytes")
        except socket.error as e:
            print(f"Error sending data: {str(e)}")
            raise

    def _recv_all(self, size):
        try:
            data = bytearray()
            while len(data) < size:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise socket.error("Server closed connection")
                data.extend(packet)
            print(f"Received {len(data)} bytes")
            return bytes(data)
        except socket.error as e:
            print(f"Error receiving data: {str(e)}")
            raise

    def get_video_list(self):
        try:
            self._send_all(bytes([Protocol.GET_LIST]))
            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            print(f"Receiving {count} videos")

            videos = []
            for _ in range(count):
                video_id = struct.unpack('!I', self._recv_all(4))[0]

                # Read video info
                segment_amount = struct.unpack('!I', self._recv_all(4))[0]
                segment_length = struct.unpack('!B', self._recv_all(1))[0]
                max_quality = struct.unpack('!B', self._recv_all(1))[0]

                # Read author
                author_len = struct.unpack('!I', self._recv_all(4))[0]
                author = self._recv_all(author_len).decode('utf-8')

                # Read title
                title_len = struct.unpack('!I', self._recv_all(4))[0]
                title = self._recv_all(title_len).decode('utf-8')

                # Read description
                desc_len = struct.unpack('!I', self._recv_all(4))[0]
                description = self._recv_all(desc_len).decode('utf-8')

                print(f"Video ID: {video_id}, Title: {title}, Author: {author}")
                videos.append((video_id, (segment_amount, segment_length, max_quality, author, title, description)))

            return videos
        except Exception as e:
            print(f"Error getting video list: {str(e)}")
            return None

    def get_video_segment(self, video_id, segment_id, quality=0):
        try:
            self._send_all(bytes([Protocol.GET_CHUNK]))
            self._send_all(struct.pack('!IIB', video_id, segment_id, quality))

            size_data = self._recv_all(4)
            if not size_data:
                return None

            size = struct.unpack('!I', size_data)[0]
            if size == 0:
                return None

            segment_data = self._recv_all(size)
            print(f"Received segment {segment_id} of video {video_id}, size: {size} bytes")
            return segment_data
        except Exception as e:
            print(f"Error getting video segment: {str(e)}")
            return None

    def login(self, username, password):
        try:
            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')

            data = bytes([Protocol.LOGIN])
            data += struct.pack('!I', len(username_bytes)) + username_bytes
            data += struct.pack('!I', len(password_bytes)) + password_bytes

            self._send_all(data)

            response = self._recv_all(1)[0]

            if response == Protocol.LOGIN_SUCCESS:
                token_len = struct.unpack('!I', self._recv_all(4))[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                print("Login successful")
                return True
            elif response == Protocol.LOGIN_WRONG_PASSWORD:
                print("Wrong password")
            elif response == Protocol.LOGIN_NO_ACCOUNT:
                print("Account not found")

            return False
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    def register(self, username, password):
        try:
            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')

            data = bytes([Protocol.REGISTER])
            data += struct.pack('!I', len(username_bytes)) + username_bytes
            data += struct.pack('!I', len(password_bytes)) + password_bytes

            self._send_all(data)

            response = self._recv_all(1)[0]

            if response == Protocol.REGISTER_SUCCESS:
                token_len = struct.unpack('!I', self._recv_all(4))[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                print("Registration successful")
                return True
            elif response == Protocol.REGISTER_USERNAME_TAKEN:
                print("Username already taken")
            elif response == Protocol.REGISTER_INVALID_CREDENTIALS:
                print("Invalid credentials")

            return False
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False

    def get_user_videos(self):
        if not self.token:
            print("Not authenticated")
            return []

        try:
            token_bytes = self.token.encode('utf-8')

            self._send_all(bytes([Protocol.GET_USER_VIDEOS]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)

            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            print(f"Receiving {count} user videos")

            videos = []
            for _ in range(count):
                video_id = struct.unpack('!I', self._recv_all(4))[0]

                # Read video info
                segment_amount = struct.unpack('!I', self._recv_all(4))[0]
                segment_length = struct.unpack('!B', self._recv_all(1))[0]
                max_quality = struct.unpack('!B', self._recv_all(1))[0]

                # Read author
                author_len = struct.unpack('!I', self._recv_all(4))[0]
                author = self._recv_all(author_len).decode('utf-8')

                # Read title
                title_len = struct.unpack('!I', self._recv_all(4))[0]
                title = self._recv_all(title_len).decode('utf-8')

                # Read description
                desc_len = struct.unpack('!I', self._recv_all(4))[0]
                description = self._recv_all(desc_len).decode('utf-8')

                print(f"User Video ID: {video_id}, Title: {title}")
                videos.append((video_id, (segment_amount, segment_length, max_quality, author, title, description)))

            return videos
        except Exception as e:
            print(f"Error getting user videos: {str(e)}")
            return []


