from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QDialog
from PyQt5.QtMultimedia import QMediaPlayer
from .network import NetworkClient
from .player import VideoPlayer
from .ui import VideoPlayerUI, LoginDialog
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
        self.is_authenticated = False

        # Connect player to UI
        self.player.video_widget.setParent(self.ui.video_widget)
        self.ui.video_widget.layout().addWidget(self.player.video_widget)
        self.player.video_widget.show()

        self._setup_ui()
        self._connect_signals()
        logger.info("VideoClient initialized")

    def _setup_ui(self):
        self.ui.play_btn.setEnabled(False)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)
        self._update_auth_ui()

    def _connect_signals(self):
        self.ui.connect_btn.clicked.connect(self.connect_to_server)
        self.ui.disconnect_btn.clicked.connect(self.disconnect_from_server)
        self.ui.login_btn.clicked.connect(self.handle_auth)
        self.ui.play_btn.clicked.connect(self.play_video)
        self.ui.pause_btn.clicked.connect(self.pause_video)
        self.ui.stop_btn.clicked.connect(self.stop_video)
        self.ui.video_list_widget.itemClicked.connect(self.select_video)
        self.player.media_player.stateChanged.connect(self.on_player_state_changed)
        self.ui.progress_slider.sliderMoved.connect(self.seek_video)

    def _update_auth_ui(self):
        if self.is_authenticated:
            self.ui.login_btn.setText("Выйти")
            self.ui.video_list_label.setText("Доступные видео (авторизован)")
        else:
            self.ui.login_btn.setText("Войти")
            self.ui.video_list_label.setText("Доступные видео")

    def connect_to_server(self):
        try:
            server_address = self.ui.server_input.text()
            host, port = server_address.split(':')
            self.network.host = host
            self.network.port = int(port)

            if self.network.connect():
                self.ui.set_connection_state(True)
                self.load_video_list()
                self.ui.status_label.setText("Успешно подключено к серверу")
        except Exception as e:
            self.ui.status_label.setText(f"Ошибка подключения: {str(e)}")

    def disconnect_from_server(self):
        try:
            self.network.disconnect()
            self.ui.set_connection_state(False)
            self.ui.set_auth_state(False)
            self.ui.video_list_widget.clear()
            self.ui.video_info_label.setText("Выберите видео из списка")
            self.ui.status_label.setText("Отключено от сервера")
        except Exception as e:
            self.ui.status_label.setText(f"Ошибка отключения: {str(e)}")

    def handle_auth(self):
        if self.is_authenticated:
            self.is_authenticated = False
            self.ui.set_auth_state(False)
            self.ui.status_label.setText("Вы вышли из системы")
            return

        if not self.network.is_connected():
            self.ui.status_label.setText("Сначала подключитесь к серверу")
            return

        login_dialog = LoginDialog(self.ui.main_widget)
        if login_dialog.exec_() == QDialog.Accepted:
            username, password = login_dialog.get_credentials()
            try:
                self.is_authenticated = self.network.login(username, password)
                self.ui.set_auth_state(self.is_authenticated)
                status_msg = "Авторизация успешна" if self.is_authenticated else "Неверные данные"
                self.ui.status_label.setText(status_msg)

                if self.is_authenticated:
                    self.load_video_list()
            except Exception as e:
                self.ui.status_label.setText(f"Ошибка авторизации: {str(e)}")

    def load_video_list(self):
        try:
            self.video_list = self.network.get_video_list()
            if self.video_list:
                self.ui.video_list_widget.clear()
                for video_id, video_info in self.video_list:
                    self.ui.video_list_widget.addItem(f"{video_id}: {video_info.title}")
        except Exception as e:
            logger.error(f"Ошибка загрузки списка видео: {str(e)}")
            QMessageBox.critical(self.ui.main_widget, "Ошибка", f"Не удалось загрузить список видео: {str(e)}")

    def select_video(self, item):
        index = self.ui.video_list_widget.row(item)
        self.current_video_id, video_info = self.video_list[index]
        self.ui.play_btn.setEnabled(True)
        self.ui.video_info_label.setText(
            f"Название: {video_info.title}\n"
            f"Автор: {video_info.author}\n"
            f"Длительность: {video_info.segment_amount * video_info.segment_length} сек"
        )

    def play_video(self):
        if not self.current_video_id:
            return

        try:
            segment_data = self.network.get_video_segment(self.current_video_id, 0, 0)
            if segment_data:
                video_info = self.video_list[self.ui.video_list_widget.currentRow()][1]
                self.player.start_playback(
                    self.current_video_id,
                    video_info.segment_length,
                    video_info.segment_amount
                )
                self.player.play_segment(segment_data)
                self.ui.progress_slider.setMaximum(video_info.segment_amount * video_info.segment_length * 1000)
                self.position_timer.start(1000)
        except Exception as e:
            logger.error(f"Ошибка воспроизведения видео: {str(e)}")
            QMessageBox.critical(self.ui.main_widget, "Ошибка", f"Не удалось воспроизвести видео: {str(e)}")

    def update_position(self):
        position = self.player.media_player.position()
        duration = self.player.media_player.duration()
        self.ui.progress_slider.setValue(position)
        self.ui.current_time.setText(f"{position // 60000:02d}:{(position % 60000) // 1000:02d}")
        self.ui.duration.setText(f"{duration // 60000:02d}:{(duration % 60000) // 1000:02d}")

    def seek_video(self, position):
        self.player.media_player.setPosition(position)

    def pause_video(self):
        self.player.media_player.pause()

    def stop_video(self):
        self.player.stop_playback()
        self.position_timer.stop()
        self.ui.progress_slider.setValue(0)
        self.ui.current_time.setText("00:00")
        self.ui.duration.setText("00:00")

    def on_player_state_changed(self, state):
        self.ui.play_btn.setEnabled(state != QMediaPlayer.PlayingState)
        self.ui.pause_btn.setEnabled(state == QMediaPlayer.PlayingState)
        self.ui.stop_btn.setEnabled(state != QMediaPlayer.StoppedState)