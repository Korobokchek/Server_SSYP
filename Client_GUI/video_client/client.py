from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtWidgets import QMessageBox, QDialog, QShortcut, QApplication
from PyQt5.QtGui import QKeySequence
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from .network import NetworkClient
from .player import VideoPlayer
from .ui import VideoPlayerUI, LoginDialog, UserAccountDialog, RegisterDialog, UploadDialog, EditVideoDialog
from .protocols import Protocol, VideoInfo
from .logger import logger
import tempfile
import os
from datetime import timedelta


class VideoClient:
    def __init__(self):
        self.network = NetworkClient()
        self.player = VideoPlayer()
        self.player.set_network(self.network)
        self.ui = VideoPlayerUI()
        self.current_video_id = None
        self.video_list = []
        self.user_videos = []
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_position)
        self.is_authenticated = False
        self.current_segment = 0
        self.segment_length = 0
        self.total_segments = 0
        self.username = None

        # Подключение плеера к UI
        self.player.video_widget.setParent(self.ui.video_widget)
        self.ui.video_widget.layout().addWidget(self.player.video_widget)
        self.player.video_widget.show()

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        logger.info("VideoClient initialized")

    def _setup_ui(self):
        self.ui.play_btn.setEnabled(False)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)
        self.ui.account_btn.setEnabled(False)

    def _connect_signals(self):
        self.ui.connect_btn.clicked.connect(self.connect_to_server)
        self.ui.disconnect_btn.clicked.connect(self.disconnect_from_server)
        self.ui.login_btn.clicked.connect(self.handle_auth)
        self.ui.register_btn.clicked.connect(self.handle_register)
        self.ui.account_btn.clicked.connect(self.show_user_account)
        self.ui.play_btn.clicked.connect(self.play_video)
        self.ui.pause_btn.clicked.connect(self.pause_video)
        self.ui.stop_btn.clicked.connect(self.stop_video)
        self.ui.video_list_widget.itemClicked.connect(self.select_video)
        self.player.media_player.stateChanged.connect(self.on_player_state_changed)
        self.player.media_player.positionChanged.connect(self.update_position)
        self.player.media_player.mediaStatusChanged.connect(self.handle_media_status)
        self.ui.progress_slider.sliderMoved.connect(self.seek_video)

    def _setup_shortcuts(self):
        self.fullscreen_shortcut = QShortcut(QKeySequence("f"), self.ui.main_widget)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self.ui.main_widget)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)

    def toggle_fullscreen(self):
        if self.ui.main_widget.window().isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        self.ui.main_widget.window().showFullScreen()
        self.player.setFullScreen(True)

    def exit_fullscreen(self):
        self.ui.main_widget.window().showNormal()
        self.player.setFullScreen(False)

    def connect_to_server(self):
        try:
            server_address = self.ui.server_input.text()
            host, port = server_address.split(':')
            self.network.host = host
            self.network.port = int(port)

            if self.network.connect():
                self.ui.connect_btn.setEnabled(False)
                self.ui.disconnect_btn.setEnabled(True)
                self.ui.login_btn.setEnabled(True)
                self.ui.register_btn.setEnabled(True)

                self.load_video_list()
                self.ui.status_label.setText("Успешно подключено к серверу")
        except Exception as e:
            self.ui.status_label.setText(f"Ошибка подключения: {str(e)}")
            logger.error(f"Connection error: {str(e)}")

    def disconnect_from_server(self):
        try:
            self.network.disconnect()
            self.ui.connect_btn.setEnabled(True)
            self.ui.disconnect_btn.setEnabled(False)
            self.ui.login_btn.setEnabled(False)
            self.ui.register_btn.setEnabled(False)
            self.ui.set_auth_state(False)
            self.ui.video_list_widget.clear()
            self.ui.video_info_label.setText("Выберите видео из списка")
            self.ui.status_label.setText("Отключено от сервера")
            self.stop_video()
            self.is_authenticated = False
            self.username = None
        except Exception as e:
            self.ui.status_label.setText(f"Ошибка отключения: {str(e)}")
            logger.error(f"Disconnection error: {str(e)}")

    def handle_auth(self):
        if self.is_authenticated:
            self.is_authenticated = False
            self.username = None
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
                    self.username = username
                    self.load_video_list()
                    self.load_user_videos()
            except Exception as e:
                self.ui.status_label.setText(f"Ошибка авторизации: {str(e)}")
                logger.error(f"Auth error: {str(e)}")

    def handle_register(self):
        if not self.network.is_connected():
            self.ui.status_label.setText("Сначала подключитесь к серверу")
            return

        register_dialog = RegisterDialog(self.ui.main_widget)
        if register_dialog.exec_() == QDialog.Accepted:
            username, password = register_dialog.get_credentials()
            try:
                success = self.network.register(username, password)
                if success:
                    self.ui.status_label.setText("Регистрация успешна. Теперь вы можете войти.")
                else:
                    self.ui.status_label.setText("Ошибка регистрации (возможно, имя уже занято)")
            except Exception as e:
                self.ui.status_label.setText(f"Ошибка регистрации: {str(e)}")
                logger.error(f"Registration error: {str(e)}")

    def show_user_account(self):
        if not self.is_authenticated:
            return

        dialog = UserAccountDialog(self.ui.main_widget)
        dialog.set_videos(self.user_videos)
        if dialog.exec_() == QDialog.Accepted:
            selected_video = dialog.get_selected_video()
            if selected_video:
                self.current_video_id, video_info = selected_video
                self.segment_length = video_info.segment_length
                self.total_segments = video_info.segment_amount
                self.ui.play_btn.setEnabled(True)
                self.ui.video_info_label.setText(
                    f"Название: {video_info.title}\n"
                    f"Автор: {video_info.author}\n"
                    f"Длительность: {self.format_duration(video_info.segment_amount * video_info.segment_length)}"
                )

    def handle_video_upload(self, video_info):
        try:
            if not hasattr(video_info, 'file_path'):
                QMessageBox.warning(self.ui.main_widget, "Ошибка", "Файл не выбран")
                return

            # Чтение файла и разбиение на сегменты
            segment_length = 10  # seconds per segment
            with open(video_info.file_path, 'rb') as f:
                video_data = f.read()

            # Простая сегментация - не работает пока :)
            segment_size = len(video_data) // 10
            segments = [video_data[i:i + segment_size] for i in range(0, len(video_data), segment_size)]

            video_info_obj = VideoInfo(
                segment_amount=len(segments),
                segment_length=segment_length,
                max_quality=0,
                author=self.username,
                title=video_info.title,
                description=video_info.description
            )

            success = self.network.upload_video(video_info_obj, segments)
            if success:
                QMessageBox.information(self.ui.main_widget, "Успех",
                                        f"Видео '{video_info.title}' успешно загружено")
                self.load_user_videos()
            else:
                QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                     "Не удалось загрузить видео")
        except Exception as e:
            QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                 f"Не удалось загрузить видео: {str(e)}")
            logger.error(f"Upload error: {str(e)}")

    def edit_video_info(self, video_id, title, description):
        try:
            success = self.network.edit_video(video_id, title, description)
            if success:
                QMessageBox.information(self.ui.main_widget, "Успех",
                                        "Информация о видео обновлена")
                self.load_user_videos()
                self.load_video_list()
            else:
                QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                     "Не удалось обновить информацию о видео")
        except Exception as e:
            QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                 f"Ошибка при обновлении видео: {str(e)}")
            logger.error(f"Edit video error: {str(e)}")

    def format_duration(self, seconds):
        return str(timedelta(seconds=seconds))

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

    def load_user_videos(self):
        if not self.is_authenticated:
            return

        try:
            self.user_videos = self.network.get_user_videos()
        except Exception as e:
            logger.error(f"Ошибка загрузки пользовательских видео: {str(e)}")
            self.user_videos = []

    def select_video(self, item):
        index = self.ui.video_list_widget.row(item)
        self.current_video_id, video_info = self.video_list[index]
        self.segment_length = video_info.segment_length
        self.total_segments = video_info.segment_amount
        self.ui.play_btn.setEnabled(True)
        self.ui.video_info_label.setText(
            f"Название: {video_info.title}\n"
            f"Автор: {video_info.author}\n"
            f"Длительность: {self.format_duration(video_info.segment_amount * video_info.segment_length)}"
        )

    def play_video(self):
        if not self.current_video_id:
            QMessageBox.warning(self.ui.main_widget, "Ошибка", "Видео не выбрано")
            return

        try:
            self.current_segment = 0
            self.ui.status_label.setText(f"Загрузка сегмента {self.current_segment + 1}/{self.total_segments}...")

            # Даем интерфейсу обновиться
            QApplication.processEvents()

            segment_data = self.network.get_video_segment(self.current_video_id, self.current_segment, 0)

            if segment_data:
                logger.info(f"Получен сегмент {self.current_segment}, размер: {len(segment_data)} байт")
                self.player.play_segment(segment_data)
                self.player.start_playback(self.current_video_id, self.segment_length, self.total_segments)
                self.position_timer.start(100)
                self.ui.progress_slider.setMaximum(self.total_segments * self.segment_length * 1000)
                self.ui.play_btn.setEnabled(False)
                self.ui.pause_btn.setEnabled(True)
                self.ui.stop_btn.setEnabled(True)
                self.ui.status_label.setText(
                    f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")
            else:
                logger.error("Получен пустой сегмент")
                QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                     "Не удалось получить сегмент видео. Сервер не вернул данные.")
        except Exception as e:
            logger.error(f"Ошибка воспроизведения видео: {str(e)}", exc_info=True)
            QMessageBox.critical(self.ui.main_widget, "Ошибка", f"Не удалось воспроизвести видео: {str(e)}")

    def handle_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            if self.current_segment < self.total_segments - 1:
                self.current_segment += 1
                try:
                    segment_data = self.network.get_video_segment(
                        self.current_video_id,
                        self.current_segment,
                        0
                    )
                    if segment_data:
                        self.player.play_segment(segment_data)
                        self.ui.status_label.setText(
                            f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")
                except Exception as e:
                    self.stop_video()
                    QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                         f"Не удалось загрузить следующий сегмент: {str(e)}")
            else:
                self.stop_video()
                QMessageBox.information(
                    self.ui.main_widget,
                    "Воспроизведение завершено",
                    "Видео закончилось"
                )

    def update_position(self, position=None):
        if position is None:
            position = self.player.media_player.position()

        self.ui.progress_slider.setValue(position)

        total_ms = (self.current_segment * self.segment_length * 1000) + position
        total_seconds = total_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        self.ui.current_time.setText(f"{minutes:02d}:{seconds:02d}")

        total_duration = self.total_segments * self.segment_length
        dur_minutes = total_duration // 60
        dur_seconds = total_duration % 60
        self.ui.duration.setText(f"{dur_minutes:02d}:{dur_seconds:02d}")

    def seek_video(self, position):
        segment_ms = self.segment_length * 1000
        new_segment = position // segment_ms
        segment_pos = position % segment_ms

        if new_segment != self.current_segment:
            self.current_segment = new_segment
            try:
                segment_data = self.network.get_video_segment(
                    self.current_video_id,
                    self.current_segment,
                    0
                )
                if segment_data:
                    self.player.play_segment(segment_data)
                    self.player.media_player.setPosition(segment_pos)
                    self.ui.status_label.setText(
                        f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")
            except Exception as e:
                logger.error(f"Ошибка перехода к сегменту {self.current_segment}: {str(e)}")
        else:
            self.player.media_player.setPosition(segment_pos)

    def pause_video(self):
        self.player.media_player.pause()
        self.ui.play_btn.setEnabled(True)
        self.ui.pause_btn.setEnabled(False)

    def stop_video(self):
        self.player.stop_playback()
        self.position_timer.stop()
        self.ui.progress_slider.setValue(0)
        self.ui.current_time.setText("00:00")
        self.ui.duration.setText("00:00")
        self.current_segment = 0
        self.ui.play_btn.setEnabled(True)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)

    def on_player_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.ui.play_btn.setEnabled(False)
            self.ui.pause_btn.setEnabled(True)
            self.ui.stop_btn.setEnabled(True)
        elif state == QMediaPlayer.PausedState:
            self.ui.play_btn.setEnabled(True)
            self.ui.pause_btn.setEnabled(False)
            self.ui.stop_btn.setEnabled(True)
        else:  # StoppedState
            self.ui.play_btn.setEnabled(True)
            self.ui.pause_btn.setEnabled(False)
            self.ui.stop_btn.setEnabled(False)