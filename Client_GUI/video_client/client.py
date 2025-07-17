from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtMultimedia import QMediaPlayer
from .network import NetworkClient
from .player import VideoPlayer
from .ui import VideoPlayerUI
from .protocols import Protocol
from .logger import logger


class VideoClient:
    def __init__(self):
        self.network = NetworkClient()
        self.player = VideoPlayer()
        self.ui = VideoPlayerUI()
        self.current_video_id = None
        self.video_list = []
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_position)

        self._setup_ui()
        self._connect_signals()
        logger.info("VideoClient initialized")

    def _setup_ui(self):
        self.ui.play_btn.setEnabled(False)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)

    def _connect_signals(self):
        self.ui.connect_btn.clicked.connect(self.connect_to_server)
        self.ui.play_btn.clicked.connect(self.play_video)
        self.ui.pause_btn.clicked.connect(self.pause_video)
        self.ui.stop_btn.clicked.connect(self.stop_video)
        self.ui.video_list_widget.itemClicked.connect(self.select_video)
        self.player.media_player.stateChanged.connect(self.on_player_state_changed)

    def connect_to_server(self):
        try:
            if self.network.connect():
                self.load_video_list()
        except Exception as e:
            QMessageBox.critical(self.ui.main_widget, "Error", f"Connection failed: {str(e)}")

    def load_video_list(self):
        try:
            self.video_list = self.network.get_video_list()
            if self.video_list:
                self.ui.video_list_widget.clear()
                for video_id, video_info in self.video_list:
                    self.ui.video_list_widget.addItem(f"{video_id}: {video_info.title}")
        except Exception as e:
            logger.error(f"Failed to load video list: {str(e)}")

    def select_video(self, item):
        index = self.ui.video_list_widget.row(item)
        self.current_video_id, video_info = self.video_list[index]
        self.ui.play_btn.setEnabled(True)
        self.ui.video_info_label.setText(
            f"Title: {video_info.title}\n"
            f"Author: {video_info.author}\n"
            f"Duration: {video_info.segment_amount * video_info.segment_length} sec"
        )

    def play_video(self):
        if not self.current_video_id:
            return

        try:
            # Get first segment
            segment_data = self.network.get_video_segment(self.current_video_id, 0, 0)
            if segment_data:
                self.player.start_playback(
                    self.current_video_id,
                    self.video_list[self.ui.video_list_widget.currentRow()][1].segment_length
                )
                self.player.play_segment(segment_data)
                self.position_timer.start(1000)
        except Exception as e:
            logger.error(f"Failed to play video: {str(e)}")

    def update_position(self):
        position = self.player.media_player.position()
        duration = self.player.media_player.duration()
        self.ui.progress_slider.setValue(position)
        self.ui.time_label.setText(
            f"{position // 60000:02d}:{(position % 60000) // 1000:02d}/"
            f"{duration // 60000:02d}:{(duration % 60000) // 1000:02d}"
        )

    def pause_video(self):
        self.player.media_player.pause()

    def stop_video(self):
        self.player.stop_playback()
        self.position_timer.stop()
        self.ui.progress_slider.setValue(0)

    def on_player_state_changed(self, state):
        self.ui.play_btn.setEnabled(state != QMediaPlayer.PlayingState)
        self.ui.pause_btn.setEnabled(state == QMediaPlayer.PlayingState)
        self.ui.stop_btn.setEnabled(state != QMediaPlayer.StoppedState)