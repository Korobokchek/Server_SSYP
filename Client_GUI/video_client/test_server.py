import socket
import threading
import struct
import random
from collections import defaultdict


class TestVideoServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.videos = {
            1: {
                'segment_amount': 10,
                'segment_length': 10,
                'max_quality': 2,
                'author': "Test Author",
                'title': "Test Video 1",
                'description': "Sample video 1",
                'segments': defaultdict(dict)
            },
            2: {
                'segment_amount': 15,
                'segment_length': 10,
                'max_quality': 1,
                'author': "Another Author",
                'title': "Demo Video",
                'description': "Demo video description",
                'segments': defaultdict(dict)
            }
        }
        print(f"Test server initialized on {host}:{port}")

    def _pack_video_info(self, video):
        """Pack video info to binary format"""
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

    def _handle_get_list(self, client_socket):
        """Handle video list request"""
        try:
            # Send video count (4 bytes)
            client_socket.sendall(struct.pack('!I', len(self.videos)))

            # Send info for each video
            for video_id, video in self.videos.items():
                # Send video ID (4 bytes)
                client_socket.sendall(struct.pack('!I', video_id))

                # Pack and send video info
                video_info = self._pack_video_info(video)

                # Send info size (4 bytes) then data
                client_socket.sendall(struct.pack('!I', len(video_info)))
                client_socket.sendall(video_info)
        except Exception as e:
            print(f"Error sending video list: {e}")

    def _handle_connection(self, client_socket, address):
        """Handle client connection"""
        print(f"New connection from {address}")
        try:
            while self.running:
                command = client_socket.recv(1)
                if not command:
                    break

                cmd = command[0]

                if cmd == 0x02:  # GET_LIST
                    self._handle_get_list(client_socket)
                else:
                    print(f"Unsupported command: {cmd}")
                    break

        except ConnectionResetError:
            print(f"Client {address} disconnected")
        finally:
            client_socket.close()

    def start(self):
        """Start the server"""
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
        """Stop the server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("Server stopped")


if __name__ == "__main__":
    server = TestVideoServer()
    server.start()