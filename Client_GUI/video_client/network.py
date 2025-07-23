import socket
import struct
import os
from .protocols import VideoInfo, Protocol
from .logger import logger


class NetworkClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.token = None
        logger.info(f"Initializing NetworkClient for {host}:{port}")

    def is_connected(self):
        return self.socket is not None

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            logger.info("Successfully connected to server")
            return True
        except socket.error as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
                logger.info("Disconnected from server")
            except socket.error as e:
                logger.error(f"Disconnection error: {str(e)}")
            finally:
                self.socket = None
                self.token = None

    def _send_all(self, data):
        try:
            self.socket.sendall(data)
            logger.debug(f"Sent {len(data)} bytes")
        except socket.error as e:
            logger.error(f"Error sending data: {str(e)}")
            raise

    def _recv_all(self, size):
        try:
            data = bytearray()
            while len(data) < size:
                packet = self.socket.recv(size - len(data))
                if not packet:
                    raise socket.error("Server closed connection")
                data.extend(packet)
            logger.debug(f"Received {len(data)} bytes")
            return bytes(data)
        except socket.error as e:
            logger.error(f"Error receiving data: {str(e)}")
            raise

    def get_video_info(self, video_id):
        try:
            self._send_all(bytes([Protocol.GET_INFO]))
            self._send_all(struct.pack('!I', video_id))

            # Чтение video info
            video_info_data = self._recv_all(4 + 1 + 1)  # segment_amount, segment_length, max_quality
            if not video_info_data:
                return None

            offset = 0
            segment_amount = struct.unpack_from('!I', video_info_data, offset)[0]
            offset += 4
            segment_length = struct.unpack_from('!B', video_info_data, offset)[0]
            offset += 1
            max_quality = struct.unpack_from('!B', video_info_data, offset)[0]
            offset += 1

            # Автор
            author_len = struct.unpack('!I', self._recv_all(4))[0]
            author = self._recv_all(author_len).decode('utf-8')

            # Титл
            title_len = struct.unpack('!I', self._recv_all(4))[0]
            title = self._recv_all(title_len).decode('utf-8')

            # Описание
            desc_len = struct.unpack('!I', self._recv_all(4))[0]
            description = self._recv_all(desc_len).decode('utf-8')

            return VideoInfo(segment_amount, segment_length, max_quality, author, title, description)
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            return None

    def get_video_segment(self, video_id, segment_id, quality):
        try:
            self._send_all(bytes([Protocol.GET_CHUNK]))
            self._send_all(struct.pack('!IIB', video_id, segment_id, quality))

            size_data = self._recv_all(4)
            if not size_data:
                return None

            size = struct.unpack('!I', size_data)[0]
            if size == 0:
                return None

            return self._recv_all(size)
        except Exception as e:
            logger.error(f"Error getting video segment: {str(e)}")
            return None

    def get_video_list(self):
        try:
            self._send_all(bytes([Protocol.GET_LIST]))

            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            logger.info(f"Receiving {count} videos")

            videos = []
            for _ in range(count):
                video_id = struct.unpack('!I', self._recv_all(4))[0]

                # Чтение video info
                segment_amount = struct.unpack('!I', self._recv_all(4))[0]
                segment_length = struct.unpack('!B', self._recv_all(1))[0]
                max_quality = struct.unpack('!B', self._recv_all(1))[0]

                # Автор
                author_len = struct.unpack('!I', self._recv_all(4))[0]
                author = self._recv_all(author_len).decode('utf-8')

                # Титл
                title_len = struct.unpack('!I', self._recv_all(4))[0]
                title = self._recv_all(title_len).decode('utf-8')

                # Описание
                desc_len = struct.unpack('!I', self._recv_all(4))[0]
                description = self._recv_all(desc_len).decode('utf-8')

                video_info = VideoInfo(segment_amount, segment_length, max_quality, author, title, description)
                videos.append((video_id, video_info))

            return videos
        except Exception as e:
            logger.error(f"Error getting video list: {str(e)}")
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
                logger.info("Login successful")
                return True
            elif response == Protocol.LOGIN_WRONG_PASSWORD:
                logger.warning("Wrong password")
            elif response == Protocol.LOGIN_NO_ACCOUNT:
                logger.warning("Account not found")

            return False
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
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
                logger.info("Registration successful")
                return True
            elif response == Protocol.REGISTER_USERNAME_TAKEN:
                logger.warning("Username already taken")
            elif response == Protocol.REGISTER_INVALID_CREDENTIALS:
                logger.warning("Invalid credentials")

            return False
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False

    def upload_video(self, video_info, segments, progress_callback=None):
        if not self.token:
            return False

        try:
            token_bytes = self.token.encode('utf-8')
            title_bytes = video_info.title.encode('utf-8')
            desc_bytes = video_info.description.encode('utf-8')

            # Calculate total size
            total_size = sum(len(segment) for segment in segments)

            # Send initial data
            self._send_all(bytes([Protocol.UPLOAD]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', len(title_bytes)) + title_bytes)
            self._send_all(struct.pack('!I', len(desc_bytes)) + desc_bytes)
            self._send_all(struct.pack('!Q', total_size))

            # Send segments with progress updates
            sent_bytes = 0
            for segment in segments:
                self._send_all(segment)
                sent_bytes += len(segment)

                # Calculate and report progress
                progress = int((sent_bytes / total_size) * 100)
                if progress_callback and not progress_callback(progress):
                    logger.info("Upload canceled by user")
                    return False

                # Wait for server progress confirmation
                response = self._recv_all(2)
                if not response or response[0] != Protocol.UPLOAD_PROGRESS:
                    logger.error("Invalid progress response from server")
                    return False

            # Get final response
            response = self._recv_all(5)
            if not response or response[0] != Protocol.UPLOAD_SUCCESS:
                logger.error("Upload failed")
                return False

            video_id = struct.unpack('!I', response[1:5])[0]
            return video_id

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}", exc_info=True)
            return False


    def get_user_videos(self):
        if not self.token:
            return []

        try:
            token_bytes = self.token.encode('utf-8')

            self._send_all(bytes([Protocol.GET_USER_VIDEOS]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)

            count_data = self._recv_all(4)
            count = struct.unpack('!I', count_data)[0]
            logger.info(f"Receiving {count} user videos")

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

                video_info = VideoInfo(segment_amount, segment_length, max_quality, author, title, description)
                videos.append((video_id, video_info))

            return videos
        except Exception as e:
            logger.error(f"Error getting user videos: {str(e)}")
            return []

    def edit_video(self, video_id, title, description):
        if not self.token:
            return False

        try:
            token_bytes = self.token.encode('utf-8')
            title_bytes = title.encode('utf-8')
            desc_bytes = description.encode('utf-8')

            self._send_all(bytes([Protocol.EDIT_VIDEO]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', video_id))
            self._send_all(struct.pack('!I', len(title_bytes)) + title_bytes)
            self._send_all(struct.pack('!I', len(desc_bytes)) + desc_bytes)

            response = self._recv_all(1)[0]
            return response == 1
        except Exception as e:
            logger.error(f"Error editing video: {str(e)}")
            return False