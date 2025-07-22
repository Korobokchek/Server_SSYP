from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget
import tempfile
import os
from .logger import logger


class VideoPlayer:
    """Класс обработки бинарного сегмента"""
    def __init__(self):
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")

        # Созданние конйтенера для поддержки полноэкранного режима
        self.container = QWidget()
        self.container.setLayout(QVBoxLayout())
        self.container.layout().setContentsMargins(0, 0, 0, 0)
        self.container.layout().addWidget(self.video_widget)

        self.media_player.setVideoOutput(self.video_widget)
        self.current_video_id = None
        self.current_segment_length = 1
        self.total_segments = 0
        self.network = None
        self.temp_files = []
        self.playlist_position = 0

        # Очистка временных файлов при завершении
        self.media_player.destroyed.connect(self.cleanup_temp_files)

        logger.info("VideoPlayer initialized")

    def set_network(self, network):
        self.network = network

    def setFullScreen(self, enabled):
        self.video_widget.setFullScreen(enabled)

    def play_segment(self, segment_data):
        try:
            if not segment_data:
                raise ValueError("Empty segment data provided")

            if len(segment_data) < 100:  # Минимальный размер для видео
                raise ValueError(f"Segment data too small: {len(segment_data)} bytes")

            # Очищаем предыдущие временные файлы
            self.cleanup_temp_files()

            # Создаем новый временный файл
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            temp_file.write(segment_data)
            temp_file.close()
            self.temp_files.append(temp_file.name)

            # Проверяем существование файла
            if not os.path.exists(temp_file.name):
                raise FileNotFoundError(f"Temp file not created: {temp_file.name}")

            # Воспроизводим видео
            media_content = QMediaContent(QUrl.fromLocalFile(temp_file.name))
            self.media_player.setMedia(media_content)
            self.media_player.play()

            logger.info(f"Playing segment from {temp_file.name} ({len(segment_data)} bytes)")
        except Exception as e:
            logger.error(f"Error playing segment: {str(e)}", exc_info=True)
            QMessageBox.critical(None, "Ошибка", f"Не удалось воспроизвести видео: {str(e)}")
            raise

    def cleanup_temp_files(self):
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting temp file {file_path}: {str(e)}")
        self.temp_files = []

    def start_playback(self, video_id, segment_length, total_segments):
        self.current_video_id = video_id
        self.current_segment_length = segment_length
        self.total_segments = total_segments
        logger.info(f"Started playback of video {video_id}")

    def stop_playback(self):
        self.media_player.stop()
        self.cleanup_temp_files()
        self.current_video_id = None
        logger.info("Playback stopped")