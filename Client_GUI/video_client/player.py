from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget
import tempfile
import os
from logger import logger


class VideoPlayer(QWidget):
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    stateChanged = pyqtSignal(QMediaPlayer.State)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_player()
        self.network = None
        self.container = self  # Add this line to expose the widget itself as container
        logger.info("VideoPlayer initialized")
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        self.layout.addWidget(self.video_widget)

    def setup_player(self):
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.setVideoOutput(self.video_widget)

        self.playlist = QMediaPlaylist()
        self.media_player.setPlaylist(self.playlist)

        self.current_video_id = None
        self.current_segment = 0
        self.segment_length = 0
        self.total_segments = 0
        self.buffered_segments = {}
        self.temp_files = []
        self.next_segment_ready = False
        self.next_segment_path = None

        self.media_player.positionChanged.connect(self.positionChanged.emit)
        self.media_player.durationChanged.connect(self.durationChanged.emit)
        self.media_player.stateChanged.connect(self.stateChanged.emit)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        self.media_player.error.connect(self.handle_error)

    def set_network(self, network):
        self.network = network

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.play_next_segment()
        elif status == QMediaPlayer.LoadedMedia:
            if self.next_segment_ready and self.next_segment_path:
                self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(self.next_segment_path)))
                self.next_segment_ready = False
                self.next_segment_path = None

    def play_next_segment(self):
        next_segment = self.current_segment + 1
        if next_segment < self.total_segments:
            if next_segment in self.buffered_segments:
                self.play_segment_from_buffer(next_segment)
            else:
                self.request_segment(next_segment)

            if next_segment + 1 < self.total_segments:
                self.buffer_segment(next_segment + 1)

    def play_segment_from_buffer(self, segment_id):
        file_path = self.buffered_segments.get(segment_id)
        if file_path and os.path.exists(file_path):
            self.playlist.clear()
            self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.media_player.play()
            self.current_segment = segment_id
            logger.info(f"Playing buffered segment {segment_id}")

    def request_segment(self, segment_id):
        if not self.network or not self.current_video_id:
            return

        def callback(segment_data):
            if segment_data:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(segment_data)
                        tmp_path = tmp_file.name
                        self.temp_files.append(tmp_path)
                        self.buffered_segments[segment_id] = tmp_path

                        if segment_id == self.current_segment + 1:
                            self.play_segment_from_buffer(segment_id)
                except Exception as e:
                    logger.error(f"Error saving segment {segment_id}: {str(e)}")

        self.network.get_video_segment_async(
            self.current_video_id,
            segment_id,
            1,  # Quality level
            callback
        )

    def buffer_segment(self, segment_id):
        if segment_id in self.buffered_segments or not self.network or not self.current_video_id:
            return

        def callback(segment_data):
            if segment_data:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(segment_data)
                        tmp_path = tmp_file.name
                        self.temp_files.append(tmp_path)
                        self.buffered_segments[segment_id] = tmp_path
                except Exception as e:
                    logger.error(f"Error buffering segment {segment_id}: {str(e)}")

        self.network.get_video_segment_async(
            self.current_video_id,
            segment_id,
            1,  # Quality level
            callback
        )

    def play_segment(self, segment_data, segment_id):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_file.write(segment_data)
                tmp_path = tmp_file.name
                self.temp_files.append(tmp_path)

                self.playlist.clear()
                self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(tmp_path)))
                self.media_player.play()
                self.current_segment = segment_id

                # Buffer next segment in advance
                if segment_id + 1 < self.total_segments:
                    self.buffer_segment(segment_id + 1)
        except Exception as e:
            logger.error(f"Error playing segment: {str(e)}")
            QMessageBox.warning(self, "Playback Error", "Could not play video segment")

    def buffer_next_segment(self, video_id, segment_id, quality, total_segments):
        if not self.network:
            return

        def callback(segment_data):
            if segment_data:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(segment_data)
                        tmp_path = tmp_file.name
                        self.temp_files.append(tmp_path)
                        self.next_segment_path = tmp_path
                        self.next_segment_ready = True
                except Exception as e:
                    logger.error(f"Error buffering next segment: {str(e)}")

        self.network.get_video_segment_async(video_id, segment_id, quality, callback)

    def stop_playback(self):
        self.media_player.stop()
        self.playlist.clear()
        self.cleanup_temp_files()
        self.current_video_id = None
        self.buffered_segments.clear()
        logger.info("Playback stopped")

    def cleanup_temp_files(self):
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting temp file {file_path}: {str(e)}")
        self.temp_files = []

    def handle_error(self, error):
        logger.error(f"Media player error: {error}")
        QMessageBox.warning(self, "Playback Error", f"An error occurred during playback: {error}")

    def position(self):
        return self.media_player.position()

    def pause(self):
        self.media_player.pause()