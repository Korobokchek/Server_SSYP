import os
import hashlib
import struct
import socket
import threading
from collections import defaultdict
from threading import Lock
import logging
from logging.handlers import RotatingFileHandler
import time
import cv2
import numpy as np

class Protocol:
    """Protocol constants"""
    GET_INFO = 0x00
    GET_CHUNK = 0x01
    GET_LIST = 0x02
    LOGIN = 0x03
    REGISTER = 0x04
    UPLOAD = 0x05
    GET_USER_VIDEOS = 0x06
    EDIT_VIDEO = 0x07

    # Login responses
    LOGIN_SUCCESS = 0x00
    LOGIN_NO_ACCOUNT = 0x01
    LOGIN_WRONG_PASSWORD = 0x02

    # Register responses
    REGISTER_SUCCESS = 0x00
    REGISTER_USERNAME_TAKEN = 0x01
    REGISTER_INVALID_CREDENTIALS = 0x02

    # Upload responses
    UPLOAD_PROGRESS = 0x00
    UPLOAD_FAILURE = 0x01
    UPLOAD_SUCCESS = 0x02

class VideoInfo:
    def __init__(self, segment_amount, segment_length, max_quality, author, title, description):
        self.segment_amount = segment_amount
        self.segment_length = segment_length
        self.max_quality = max_quality
        self.author = author
        self.title = title
        self.description = description

    @classmethod
    def from_bytes(cls, data):
        try:
            offset = 0
            segment_amount = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            segment_length = struct.unpack_from('!B', data, offset)[0]
            offset += 1
            max_quality = struct.unpack_from('!B', data, offset)[0]
            offset += 1

            # Read author
            author_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            author = data[offset:offset + author_len].decode('utf-8')
            offset += author_len

            # Read title
            title_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            title = data[offset:offset + title_len].decode('utf-8')
            offset += title_len

            # Read description
            desc_len = struct.unpack_from('!I', data, offset)[0]
            offset += 4
            description = data[offset:offset + desc_len].decode('utf-8')

            return cls(segment_amount, segment_length, max_quality, author, title, description)
        except Exception as e:
            raise ValueError(f"Failed to parse VideoInfo: {str(e)}")

    def to_bytes(self):
        try:
            author_bytes = self.author.encode('utf-8')
            title_bytes = self.title.encode('utf-8')
            description_bytes = self.description.encode('utf-8')

            data = struct.pack('!IBB',
                               self.segment_amount,
                               self.segment_length,
                               self.max_quality)
            data += struct.pack('!I', len(author_bytes)) + author_bytes
            data += struct.pack('!I', len(title_bytes)) + title_bytes
            data += struct.pack('!I', len(description_bytes)) + description_bytes
            return data
        except Exception as e:
            raise ValueError(f"Failed to serialize VideoInfo: {str(e)}")

class ClientConnection:
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.socket.settimeout(5.0)

    def close(self):
        try:
            self.socket.close()
        except:
            pass

class VideoServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.connection_lock = Lock()
        self.active_connections = set()
        self.video_dir = 'videos'
        self.segment_size = 1024 * 1024  # 1MB segments

        # Initialize logger
        self._setup_logger()
        self.logger = logging.getLogger('VideoServer')

        # Users data (username: password_hash)
        self.users = {
            'gosha': hashlib.sha256('goshagosha'.encode()).hexdigest(),
            'test': hashlib.sha256('test123'.encode()).hexdigest()
        }
        self.tokens = {}  # token: username

        # Videos data
        self.user_videos = defaultdict(list)
        self.video_info = {}
        self.video_data = {}

        # Create test videos
        self._create_test_videos()

        # Create video directory if not exists
        os.makedirs(self.video_dir, exist_ok=True)

    def _create_test_videos(self):
        """Create test videos for the server"""
        # White video (300 seconds)
        self._create_white_video(1, "White Video (300s)", 300)

        # Video for user 'gosha'
        self._create_white_video(2, "Gosha's Video (60s)", 60, author="gosha")
        self.user_videos['gosha'].append(2)

    def _create_white_video(self, video_id, title, duration, author="system"):
        """Create a white video using OpenCV"""
        segment_length = 10  # seconds per segment
        segment_count = duration // segment_length
        fps = 30
        width, height = 640, 480

        self.video_info[video_id] = {
            'segment_amount': segment_count,
            'segment_length': segment_length,
            'max_quality': 0,
            'author': author,
            'title': title,
            'description': f"White test video, {duration} seconds"
        }

        # Generate white frame
        white_frame = np.ones((height, width, 3), dtype=np.uint8) * 255

        # Create segments
        for segment_id in range(segment_count):
            # Create temporary video file for the segment
            temp_file = f"temp_segment_{video_id}_{segment_id}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_file, fourcc, fps, (width, height))

            # Write white frames for the segment duration
            for _ in range(segment_length * fps):
                out.write(white_frame)
            out.release()

            # Read segment data
            with open(temp_file, 'rb') as f:
                segment_data = f.read()

            # Store segment data
            if video_id not in self.video_data:
                self.video_data[video_id] = {}
            self.video_data[video_id][segment_id] = segment_data

            # Remove temporary file
            os.remove(temp_file)

    def _setup_logger(self):
        """Configure logging system"""
        logger = logging.getLogger('VideoServer')
        logger.setLevel(logging.DEBUG)

        os.makedirs('logs', exist_ok=True)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        file_handler = RotatingFileHandler(
            'logs/video_server.log',
            maxBytes=1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def _handle_connection(self, client_conn):
        """Handle client connection"""
        self.logger.info(f"New connection from {client_conn.address}")
        try:
            while self.running:
                try:
                    command = client_conn.socket.recv(1)
                    if not command:
                        break

                    cmd = command[0]

                    if cmd == Protocol.GET_INFO:
                        self._handle_get_info(client_conn)
                    elif cmd == Protocol.GET_CHUNK:
                        self._handle_get_chunk(client_conn)
                    elif cmd == Protocol.GET_LIST:
                        self._handle_get_list(client_conn)
                    elif cmd == Protocol.LOGIN:
                        self._handle_login(client_conn)
                    elif cmd == Protocol.REGISTER:
                        self._handle_register(client_conn)
                    elif cmd == Protocol.UPLOAD:
                        self._handle_upload(client_conn)
                    elif cmd == Protocol.GET_USER_VIDEOS:
                        self._handle_get_user_videos(client_conn)
                    elif cmd == Protocol.EDIT_VIDEO:
                        self._handle_edit_video(client_conn)
                    else:
                        self.logger.warning(f"Unknown command: {cmd}")
                        break

                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error handling command: {e}")
                    break

        except ConnectionResetError:
            self.logger.info(f"Client {client_conn.address} disconnected")
        except Exception as e:
            self.logger.error(f"Error handling client {client_conn.address}: {e}")
        finally:
            with self.connection_lock:
                if client_conn in self.active_connections:
                    self.active_connections.remove(client_conn)
            client_conn.close()

    def _handle_get_info(self, client_conn):
        """Handle GET_INFO command"""
        try:
            video_id = struct.unpack('!I', client_conn.socket.recv(4))[0]
            self.logger.info(f"Request for video info: {video_id}")

            if video_id in self.video_info:
                info = self.video_info[video_id]
                video_info = VideoInfo(
                    info['segment_amount'],
                    info['segment_length'],
                    info['max_quality'],
                    info['author'],
                    info['title'],
                    info['description']
                )
                client_conn.socket.sendall(video_info.to_bytes())
            else:
                client_conn.socket.sendall(b'')
        except Exception as e:
            self.logger.error(f"Error handling GET_INFO: {e}")
            client_conn.socket.sendall(b'')

    def _handle_get_chunk(self, client_conn):
        """Handle GET_CHUNK command"""
        try:
            video_id, segment_id, quality = struct.unpack('!IIB', client_conn.socket.recv(9))
            self.logger.info(f"Request for video {video_id}, segment {segment_id}, quality {quality}")

            if video_id in self.video_data and segment_id in self.video_data[video_id]:
                segment_data = self.video_data[video_id][segment_id]
                client_conn.socket.sendall(struct.pack('!I', len(segment_data)))
                client_conn.socket.sendall(segment_data)
            else:
                client_conn.socket.sendall(struct.pack('!I', 0))
        except Exception as e:
            self.logger.error(f"Error handling GET_CHUNK: {e}")
            client_conn.socket.sendall(struct.pack('!I', 0))

    def _handle_get_list(self, client_conn):
        """Handle GET_LIST command"""
        try:
            videos = list(self.video_info.items())
            client_conn.socket.sendall(struct.pack('!I', len(videos)))

            for video_id, info in videos:
                video_info = VideoInfo(
                    info['segment_amount'],
                    info['segment_length'],
                    info['max_quality'],
                    info['author'],
                    info['title'],
                    info['description']
                )
                video_info_data = video_info.to_bytes()

                client_conn.socket.sendall(struct.pack('!I', video_id))
                client_conn.socket.sendall(video_info_data)
        except Exception as e:
            self.logger.error(f"Error handling GET_LIST: {e}")

    def _handle_login(self, client_conn):
        """Handle LOGIN command"""
        try:
            # Read username
            username_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            username = client_conn.socket.recv(username_len).decode('utf-8')

            # Read password
            password_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            password = client_conn.socket.recv(password_len).decode('utf-8')

            if username not in self.users:
                client_conn.socket.sendall(bytes([Protocol.LOGIN_NO_ACCOUNT]))
                return

            stored_hash = self.users[username]
            input_hash = hashlib.sha256(password.encode()).hexdigest()

            if input_hash != stored_hash:
                client_conn.socket.sendall(bytes([Protocol.LOGIN_WRONG_PASSWORD]))
                return

            # Generate new token
            token = hashlib.sha256(os.urandom(32)).hexdigest()
            self.tokens[token] = username

            # Send success response
            client_conn.socket.sendall(bytes([Protocol.LOGIN_SUCCESS]))
            token_bytes = token.encode('utf-8')
            client_conn.socket.sendall(struct.pack('!I', len(token_bytes)))
            client_conn.socket.sendall(token_bytes)

            self.logger.info(f"User {username} logged in successfully")
        except Exception as e:
            self.logger.error(f"Error handling LOGIN: {e}")

    def _handle_register(self, client_conn):
        """Handle REGISTER command"""
        try:
            # Read username
            username_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            username = client_conn.socket.recv(username_len).decode('utf-8')

            # Read password
            password_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            password = client_conn.socket.recv(password_len).decode('utf-8')

            # Validate
            if not username or not password or len(username) > 50 or len(password) > 100:
                client_conn.socket.sendall(bytes([Protocol.REGISTER_INVALID_CREDENTIALS]))
                return

            if username in self.users:
                client_conn.socket.sendall(bytes([Protocol.REGISTER_USERNAME_TAKEN]))
                return

            # Hash password
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            self.users[username] = password_hash

            # Generate token
            token = hashlib.sha256(os.urandom(32)).hexdigest()
            self.tokens[token] = username

            # Send success response
            client_conn.socket.sendall(bytes([Protocol.REGISTER_SUCCESS]))
            token_bytes = token.encode('utf-8')
            client_conn.socket.sendall(struct.pack('!I', len(token_bytes)))
            client_conn.socket.sendall(token_bytes)

            self.logger.info(f"New user registered: {username}")
        except Exception as e:
            self.logger.error(f"Error handling REGISTER: {e}")

    def _handle_upload(self, client_conn):
        """Handle UPLOAD command"""
        try:
            # Read token
            token_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            token = client_conn.socket.recv(token_len).decode('utf-8')

            # Find user by token
            username = self.tokens.get(token)
            if not username:
                client_conn.socket.sendall(bytes([Protocol.UPLOAD_FAILURE]))
                return

            # Read title
            title_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            title = client_conn.socket.recv(title_len).decode('utf-8')

            # Read description
            desc_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            description = client_conn.socket.recv(desc_len).decode('utf-8')

            # Read file size
            file_size = struct.unpack('!Q', client_conn.socket.recv(8))[0]
            self.logger.info(f"Starting upload: {title}, size: {file_size} bytes")

            # Create video directory if not exists
            video_dir = os.path.join(self.video_dir, username)
            os.makedirs(video_dir, exist_ok=True)

            # Generate video ID
            video_id = max(self.video_info.keys()) + 1 if self.video_info else 1

            # Receive file in chunks
            received = 0
            segments = []
            segment_id = 0

            while received < file_size:
                chunk_size = min(self.segment_size, file_size - received)
                chunk = client_conn.socket.recv(chunk_size)
                if not chunk:
                    break

                segments.append(chunk)
                received += len(chunk)

                # Send progress update
                progress = int((received / file_size) * 100)
                client_conn.socket.sendall(bytes([Protocol.UPLOAD_PROGRESS, progress]))

            # Calculate segment amount (assuming 10s segments)
            segment_amount = len(segments)
            segment_length = 10  # seconds

            # Save video data
            self.video_info[video_id] = {
                'segment_amount': segment_amount,
                'segment_length': segment_length,
                'max_quality': 0,
                'author': username,
                'title': title,
                'description': description,
                'created_at': time.time()
            }

            self.video_data[video_id] = {i: segment for i, segment in enumerate(segments)}
            self.user_videos[username].append(video_id)

            # Send success response
            client_conn.socket.sendall(bytes([Protocol.UPLOAD_SUCCESS]))
            client_conn.socket.sendall(struct.pack('!I', video_id))
            self.logger.info(f"Video {video_id} uploaded by {username}")

        except Exception as e:
            self.logger.error(f"Error handling UPLOAD: {e}")
            client_conn.socket.sendall(bytes([Protocol.UPLOAD_FAILURE]))

    def _handle_get_user_videos(self, client_conn):
        """Handle GET_USER_VIDEOS command"""
        try:
            # Read token
            token_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            token = client_conn.socket.recv(token_len).decode('utf-8')

            # Find user by token
            username = self.tokens.get(token)
            if not username:
                client_conn.socket.sendall(struct.pack('!I', 0))
                return

            # Send user videos
            user_videos = self.user_videos.get(username, [])
            client_conn.socket.sendall(struct.pack('!I', len(user_videos)))

            for video_id in user_videos:
                if video_id in self.video_info:
                    info = self.video_info[video_id]
                    video_info = VideoInfo(
                        info['segment_amount'],
                        info['segment_length'],
                        info['max_quality'],
                        info['author'],
                        info['title'],
                        info['description']
                    )
                    video_info_data = video_info.to_bytes()

                    client_conn.socket.sendall(struct.pack('!I', video_id))
                    client_conn.socket.sendall(video_info_data)

        except Exception as e:
            self.logger.error(f"Error handling GET_USER_VIDEOS: {e}")

    def _handle_edit_video(self, client_conn):
        """Handle EDIT_VIDEO command"""
        try:
            # Read token
            token_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            token = client_conn.socket.recv(token_len).decode('utf-8')

            # Find user by token
            username = self.tokens.get(token)
            if not username:
                client_conn.socket.sendall(bytes([0]))
                return

            # Read video ID
            video_id = struct.unpack('!I', client_conn.socket.recv(4))[0]

            # Read new title
            title_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            title = client_conn.socket.recv(title_len).decode('utf-8')

            # Read new description
            desc_len = struct.unpack('!I', client_conn.socket.recv(4))[0]
            description = client_conn.socket.recv(desc_len).decode('utf-8')

            # Update video info
            if (video_id in self.video_info and
                    self.video_info[video_id]['author'] == username):
                self.video_info[video_id]['title'] = title
                self.video_info[video_id]['description'] = description
                client_conn.socket.sendall(bytes([1]))
                self.logger.info(f"User {username} edited video {video_id}")
            else:
                client_conn.socket.sendall(bytes([0]))

        except Exception as e:
            self.logger.error(f"Error handling EDIT_VIDEO: {e}")
            client_conn.socket.sendall(bytes([0]))

    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            self.logger.info(f"Server started on {self.host}:{self.port}")

            while self.running:
                try:
                    client_socket, address = self.socket.accept()
                    client_conn = ClientConnection(client_socket, address)

                    with self.connection_lock:
                        self.active_connections.add(client_conn)

                    threading.Thread(
                        target=self._handle_connection,
                        args=(client_conn,),
                        daemon=True
                    ).start()
                except Exception as e:
                    if self.running:
                        self.logger.error(f"Error accepting connection: {e}")

        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

        with self.connection_lock:
            for conn in list(self.active_connections):
                conn.close()
            self.active_connections.clear()

        self.logger.info("Server stopped")

def main():
    # Initialize server
    server = VideoServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
    except Exception as e:
        print(f"Server crashed: {e}")
        server.stop()

if __name__ == "__main__":
    main()