from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QBuffer, QIODevice, QTimer
from .logger import logger


class VideoPlayer:
    def __init__(self):
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.buffered_segments = {}
        self.segment_timer = QTimer()
        self.segment_timer.setInterval(3000)  # 3 seconds - определение интервала принятия видео
        self.segment_timer.timeout.connect(self._buffer_next_segment)
        self.current_video_id = None
        self.current_segment_length = 1
        logger.info("VideoPlayer initialized")

    def play_segment(self, segment_data):
        try:
            buffer = QBuffer()
            buffer.setData(segment_data)
            if not buffer.open(QIODevice.ReadOnly):
                raise IOError("Failed to open buffer")

            self.media_player.setMedia(QMediaContent(), buffer)
            self.media_player.play()
        except Exception as e:
            logger.error(f"Failed to play segment: {str(e)}")
            raise

    def _buffer_next_segment(self):
        if not self.current_video_id or self.media_player.state() != QMediaPlayer.PlayingState:
            return

        current_pos = self.media_player.position() / 1000  # in seconds
        next_segment = int(current_pos // self.current_segment_length) + 1

        if next_segment not in self.buffered_segments:
            segment_data = self.network.get_video_segment(
                self.current_video_id,
                next_segment,
                0  # Default quality
            )
            if segment_data:
                self.buffered_segments[next_segment] = segment_data
                logger.debug(f"Buffered segment {next_segment}")

    def start_playback(self, video_id, segment_length):
        self.current_video_id = video_id
        self.current_segment_length = segment_length
        self.buffered_segments = {}
        self.segment_timer.start()

    def stop_playback(self):
        self.segment_timer.stop()
        self.media_player.stop()
        self.current_video_id = None