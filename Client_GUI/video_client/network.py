import socket
import struct
import os
import time
from typing import Optional, Tuple, List, Callable
import threading

from .protocols import VideoInfo, ChannelInfo, Protocol
from .logger import logger


class NetworkClient:
    def __init__(self, host: str = 'localhost', port: int = 8080):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.token: Optional[str] = None
        logger.info(f"Initializing NetworkClient for {host}:{port}")

    def is_connected(self) -> bool:
        return self.socket is not None

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.socket.setblocking(True)
            logger.info("Successfully connected to server")
            return True
        except socket.error as e:
            logger.error(f"Connection error: {str(e)}")
            self.socket = None
            return False
        finally:
            if self.socket:
                self.socket.settimeout(None)

    def disconnect(self) -> None:
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
                logger.info("Disconnected from server")
            except socket.error as e:
                logger.error(f"Disconnection error: {str(e)}")
            finally:
                self.socket = None
                self.token = None

    def _send_all(self, data: bytes) -> None:
        if not self.socket:
            raise ConnectionError("Not connected to server")

        try:
            total_sent = 0
            while total_sent < len(data):
                sent = self.socket.send(data[total_sent:])
                if sent == 0:
                    raise ConnectionError("Socket connection broken")
                total_sent += sent
            logger.debug(f"Sent {len(data)} bytes")
        except socket.error as e:
            logger.error(f"Error sending data: {str(e)}")
            self.disconnect()
            raise

    def _recv_all(self, size):
        if not self.socket:
            raise ConnectionError("Not connected to server")
        try:
            data = bytearray()
            while len(data) < size:
                remaining = size - len(data)
                packet = self.socket.recv(remaining)
                if not packet:
                    raise ConnectionError("Server closed connection")
                data.extend(packet)
            logger.debug(f"Received {len(data)} bytes")
            return bytes(data)
        except socket.error as e:
            logger.error(f"Error receiving data: {str(e)}")
            self.disconnect()
            raise

    def get_video_segment(self, video_id: int, segment_id: int, quality: int) -> Optional[bytes]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            self._send_all(bytes([Protocol.GET_VIDEO_SEGMENT]))
            self._send_all(struct.pack('!IIB', video_id, segment_id, quality))

            size_bytes = self._recv_all(4)
            size = struct.unpack('!I', size_bytes)[0]

            if size == 0:
                return None
            return self._recv_all(size)
        except Exception as e:
            logger.error(f"Error getting video segment {segment_id}: {str(e)}", exc_info=True)
            return None

    def get_video_list(self):
        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            # Всегда используем GET_VIDEO_LIST (0x02)
            cmd = Protocol.GET_VIDEO_LIST
            self._send_all(bytes([cmd]))

            # Если есть токен, отправляем его для получения персонального списка
            if self.token:
                self._send_all(struct.pack('!I', len(self.token)) + self.token.encode('utf-8'))

            count_bytes = self._recv_all(4)
            count = struct.unpack('!I', count_bytes)[0]
            logger.info(f"Receiving {count} videos")

            videos = []
            for _ in range(count):
                video_id_bytes = self._recv_all(4)
                video_id = struct.unpack('!I', video_id_bytes)[0]

                video_info_data = self._recv_video_info_data()
                video_info = self._parse_video_info(video_info_data)

                videos.append((video_id, video_info))

            return videos
        except Exception as e:
            logger.error(f"Error getting video list: {str(e)}", exc_info=True)
            return None

    def _recv_video_info_data(self) -> bytes:
        data = bytearray()
        data.extend(self._recv_all(4))  # channel_id
        data.extend(self._recv_all(4))  # segment_amount
        data.extend(self._recv_all(1))  # segment_length
        data.extend(self._recv_all(1))  # max_quality

        for _ in range(3):  # author, title, description
            length_bytes = self._recv_all(4)
            length = struct.unpack('!I', length_bytes)[0]
            data.extend(length_bytes)
            data.extend(self._recv_all(length))

        return bytes(data)

    def _parse_video_info(self, data: bytes) -> VideoInfo:
        offset = 0
        channel_id = struct.unpack_from('!I', data, offset)[0]
        offset += 4
        segment_amount = struct.unpack_from('!I', data, offset)[0]
        offset += 4
        segment_length = struct.unpack_from('!B', data, offset)[0]
        offset += 1
        max_quality = struct.unpack_from('!B', data, offset)[0]
        offset += 1

        def unpack_string():
            nonlocal offset
            length = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            string = data[offset:offset + length].decode('utf-8')
            offset += length
            return string

        author = unpack_string()
        title = unpack_string()
        description = unpack_string()

        return VideoInfo(
            channel_id=channel_id,
            segment_amount=segment_amount,
            segment_length=segment_length,
            max_quality=max_quality,
            author=author,
            title=title,
            description=description
        )

    def login(self, username: str, password: str) -> bool:
        try:
            if not self.is_connected():
                if not self.connect():
                    return False

            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')

            data = bytearray()
            data.append(Protocol.LOGIN)
            data.extend(struct.pack('!I', len(username_bytes)))
            data.extend(username_bytes)
            data.extend(struct.pack('!I', len(password_bytes)))
            data.extend(password_bytes)

            self._send_all(data)

            response = self._recv_all(1)[0]

            if response == Protocol.SUCCESS:
                token_len_bytes = self._recv_all(4)
                token_len = struct.unpack('!I', token_len_bytes)[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                logger.info("Login successful")
                return True
            elif response == Protocol.INVALID_CREDENTIALS:
                logger.warning("Wrong password")
            elif response == Protocol.FAILURE:
                logger.warning("Account not found")

            return False
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return False

    def register(self, username: str, password: str) -> bool:
        try:
            if not self.is_connected():
                if not self.connect():
                    return False

            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')

            data = bytearray()
            data.append(Protocol.REGISTER)
            data.extend(struct.pack('!I', len(username_bytes)))
            data.extend(username_bytes)
            data.extend(struct.pack('!I', len(password_bytes)))
            data.extend(password_bytes)

            self._send_all(data)

            response = self._recv_all(1)[0]

            if response == Protocol.SUCCESS:
                token_len_bytes = self._recv_all(4)
                token_len = struct.unpack('!I', token_len_bytes)[0]
                self.token = self._recv_all(token_len).decode('utf-8')
                logger.info("Registration successful")
                return True
            elif response == Protocol.USERNAME_TAKEN:
                logger.warning("Username already taken")
            elif response == Protocol.INVALID_CREDENTIALS:
                logger.warning("Invalid credentials")

            return False
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return False

    def upload_video(self, channel_id: int, title: str, description: str,
                    file_path: str, progress_callback: Callable[[int], bool]) -> Optional[int]:
        if not self.token:
            logger.warning("No token available for upload")
            return None

        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.warning("Empty file provided for upload")
                return None

            token_bytes = self.token.encode('utf-8')
            title_bytes = title.encode('utf-8')
            desc_bytes = description.encode('utf-8')

            self._send_all(bytes([Protocol.UPLOAD_VIDEO]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', channel_id))
            self._send_all(struct.pack('!I', len(title_bytes)) + title_bytes)
            self._send_all(struct.pack('!I', len(desc_bytes)) + desc_bytes)
            self._send_all(struct.pack('!Q', file_size))

            chunk_size = 1024 * 1024
            sent_bytes = 0

            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    self._send_all(chunk)
                    sent_bytes += len(chunk)

                    progress = int((sent_bytes / file_size) * 100)
                    if not progress_callback(progress):
                        logger.info("Upload canceled by user")
                        return None

                    response = self._recv_all(1)
                    if not response or response[0] != Protocol.SUCCESS:
                        logger.error("Invalid progress response from server")
                        return None

            response = self._recv_all(5)
            if not response or response[0] != Protocol.SUCCESS:
                logger.error("Upload failed")
                return None

            video_id = struct.unpack('!I', response[1:5])[0]
            logger.info(f"Successfully uploaded video with ID {video_id}")
            return video_id

        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}", exc_info=True)
            return None

    def get_channel_info(self, channel_id: int) -> Optional[ChannelInfo]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            self._send_all(bytes([Protocol.GET_CHANNEL_INFO]))
            self._send_all(struct.pack('!I', channel_id))

            name_len_bytes = self._recv_all(4)
            name_len = struct.unpack('!I', name_len_bytes)[0]
            name = self._recv_all(name_len).decode('utf-8')

            desc_len_bytes = self._recv_all(4)
            desc_len = struct.unpack('!I', desc_len_bytes)[0]
            description = self._recv_all(desc_len).decode('utf-8')

            subscribers_owner_video = self._recv_all(12)
            subscribers, owner, video_amount = struct.unpack('!III', subscribers_owner_video)

            return ChannelInfo(name, description, subscribers, owner, video_amount)
        except Exception as e:
            logger.error(f"Error getting channel info: {str(e)}", exc_info=True)
            return None

    def create_channel(self, name: str, description: str) -> Optional[int]:
        if not self.token:
            logger.warning("No token available for channel creation")
            return None

        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            token_bytes = self.token.encode('utf-8')
            name_bytes = name.encode('utf-8')
            desc_bytes = description.encode('utf-8')

            self._send_all(bytes([Protocol.CREATE_CHANNEL]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', len(name_bytes)) + name_bytes)
            self._send_all(struct.pack('!I', len(desc_bytes)) + desc_bytes)

            response = self._recv_all(5)
            if not response or response[0] != Protocol.SUCCESS:
                logger.error("Channel creation failed")
                return None

            channel_id = struct.unpack('!I', response[1:5])[0]
            logger.info(f"Successfully created channel with ID {channel_id}")
            return channel_id

        except Exception as e:
            logger.error(f"Error creating channel: {str(e)}", exc_info=True)
            return None

    def get_channel_videos(self, channel_id: int) -> Optional[List[int]]:
        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            self._send_all(bytes([Protocol.GET_CHANNEL_VIDEOS]))
            self._send_all(struct.pack('!III', channel_id, 0, 100))  # Get first 100 videos

            response = self._recv_all(1)
            if response[0] != Protocol.SUCCESS:
                logger.error("Failed to get channel videos")
                return None

            count_bytes = self._recv_all(4)
            count = struct.unpack('!I', count_bytes)[0]

            video_ids = []
            for _ in range(count):
                video_id_bytes = self._recv_all(4)
                video_id = struct.unpack('!I', video_id_bytes)[0]
                video_ids.append(video_id)

            return video_ids
        except Exception as e:
            logger.error(f"Error getting channel videos: {str(e)}", exc_info=True)
            return None

    def get_user_channels(self) -> Optional[List[Tuple[int, ChannelInfo]]]:
        if not self.token:
            return None

        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            self._send_all(bytes([Protocol.GET_USER_CHANNELS]))
            self._send_all(struct.pack('!I', len(self.token)) + self.token.encode('utf-8'))

            count_bytes = self._recv_all(4)
            count = struct.unpack('!I', count_bytes)[0]

            channels = []
            for _ in range(count):
                channel_id_bytes = self._recv_all(4)
                channel_id = struct.unpack('!I', channel_id_bytes)[0]

                name_len_bytes = self._recv_all(4)
                name_len = struct.unpack('!I', name_len_bytes)[0]
                name = self._recv_all(name_len).decode('utf-8')

                desc_len_bytes = self._recv_all(4)
                desc_len = struct.unpack('!I', desc_len_bytes)[0]
                description = self._recv_all(desc_len).decode('utf-8')

                subscribers_owner_video = self._recv_all(12)
                subscribers, owner, video_amount = struct.unpack('!III', subscribers_owner_video)

                channel_info = ChannelInfo(name, description, subscribers, owner, video_amount)
                channels.append((channel_id, channel_info))

            return channels
        except Exception as e:
            logger.error(f"Error getting user channels: {str(e)}", exc_info=True)
            return None

    def subscribe(self, channel_id: int) -> bool:
        if not self.token:
            logger.warning("No token available for subscription")
            return False

        try:
            if not self.is_connected():
                if not self.connect():
                    return False

            token_bytes = self.token.encode('utf-8')

            self._send_all(bytes([Protocol.SUBSCRIBE]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', channel_id))

            response = self._recv_all(1)[0]
            return response == Protocol.SUCCESS
        except Exception as e:
            logger.error(f"Error subscribing to channel: {str(e)}", exc_info=True)
            return False

    def unsubscribe(self, channel_id: int) -> bool:
        if not self.token:
            logger.warning("No token available for unsubscription")
            return False

        try:
            if not self.is_connected():
                if not self.connect():
                    return False

            token_bytes = self.token.encode('utf-8')

            self._send_all(bytes([Protocol.UNSUBSCRIBE]))
            self._send_all(struct.pack('!I', len(token_bytes)) + token_bytes)
            self._send_all(struct.pack('!I', channel_id))

            response = self._recv_all(1)[0]
            return response == Protocol.SUCCESS
        except Exception as e:
            logger.error(f"Error unsubscribing from channel: {str(e)}", exc_info=True)
            return False

    def get_video_segment_async(self, video_id: int, segment_id: int,
                              quality: int, callback: Callable[[Optional[bytes]], None]):
        def worker():
            try:
                segment = self.get_video_segment(video_id, segment_id, quality)
                callback(segment)
            except Exception as e:
                logger.error(f"Async segment error: {str(e)}")
                callback(None)

        thread = threading.Thread(target=worker)
        thread.start()

    def get_user_channels_by_user(self, username: str) -> Optional[List[Tuple[int, ChannelInfo]]]:
        if not self.token:
            return None

        try:
            if not self.is_connected():
                if not self.connect():
                    return None

            self._send_all(bytes([Protocol.GET_USER_CHANNELS_BY_USER]))
            self._send_all(struct.pack('!I', len(self.token)) + self.token.encode('utf-8'))
            self._send_all(struct.pack('!I', len(username.encode('utf-8'))) + username.encode('utf-8'))

            count_bytes = self._recv_all(4)
            count = struct.unpack('!I', count_bytes)[0]

            channels = []
            for _ in range(count):
                channel_id_bytes = self._recv_all(4)
                channel_id = struct.unpack('!I', channel_id_bytes)[0]

                name_len_bytes = self._recv_all(4)
                name_len = struct.unpack('!I', name_len_bytes)[0]
                name = self._recv_all(name_len).decode('utf-8')

                desc_len_bytes = self._recv_all(4)
                desc_len = struct.unpack('!I', desc_len_bytes)[0]
                description = self._recv_all(desc_len).decode('utf-8')

                subscribers_owner_video = self._recv_all(12)
                subscribers, owner, video_amount = struct.unpack('!III', subscribers_owner_video)

                channel_info = ChannelInfo(name, description, subscribers, owner, video_amount)
                channels.append((channel_id, channel_info))

            return channels
        except Exception as e:
            logger.error(f"Error getting user channels by username: {str(e)}", exc_info=True)
            return None