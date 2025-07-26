import sys
import os
import tempfile
from datetime import timedelta
from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QShortcut,
                             QProgressDialog, QFileDialog)
from PyQt5.QtGui import QKeySequence
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

from player import VideoPlayer
from .network import NetworkClient
from .ui import (VideoPlayerUI, LoginDialog, RegisterDialog,
                 UserAccountDialog, UploadDialog, EditVideoDialog,
                 ChannelDialog, CreateChannelDialog, ChannelInfoDialog)
from .logger import logger


class VideoClient:
    def __init__(self):
        self.network = NetworkClient()
        self.ui = VideoPlayerUI()
        self.setup_player()
        self.current_video_id = None
        self.video_list = []
        self.user_videos = []
        self.channels = []
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_position)
        self.is_authenticated = False
        self.current_segment = 0
        self.segment_length = 0
        self.total_segments = 0
        self.username = None
        self.current_channel_id = None

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        logger.info("VideoClient initialized")

    def setup_player(self):
        """Initialize video player components"""
        self.media_player = VideoPlayer()
        self.video_widget = self.media_player.video_widget  # Use the video_widget directly
        self.ui.video_widget.layout().addWidget(self.video_widget)
        self.media_player.set_network(self.network)

        # Connect signals
        self.media_player.media_player.stateChanged.connect(self.on_player_state_changed)
        self.media_player.media_player.positionChanged.connect(self.update_position)
        self.media_player.media_player.mediaStatusChanged.connect(self.handle_media_status)

    def _setup_ui(self):
        """Initialize UI state"""
        self.ui.play_btn.setEnabled(False)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)
        self.ui.account_btn.setEnabled(False)
        self.ui.channel_btn.setEnabled(False)

    def _connect_signals(self):
        """Connect UI signals to methods"""
        self.ui.connect_btn.clicked.connect(self.connect_to_server)
        self.ui.disconnect_btn.clicked.connect(self.disconnect_from_server)
        self.ui.login_btn.clicked.connect(self.handle_auth)
        self.ui.register_btn.clicked.connect(self.handle_register)
        self.ui.account_btn.clicked.connect(self.show_user_account)
        self.ui.channel_btn.clicked.connect(self.show_channels)
        self.ui.play_btn.clicked.connect(self.play_video)
        self.ui.pause_btn.clicked.connect(self.pause_video)
        self.ui.stop_btn.clicked.connect(self.stop_video)
        self.ui.video_list_widget.itemClicked.connect(self.select_video)
        self.ui.progress_slider.sliderMoved.connect(self.seek_video)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.fullscreen_shortcut = QShortcut(QKeySequence("f"), self.ui.main_widget)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)

        self.escape_shortcut = QShortcut(QKeySequence("Escape"), self.ui.main_widget)
        self.escape_shortcut.activated.connect(self.exit_fullscreen)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.video_widget.isFullScreen():
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode"""
        self.ui.main_widget.window().showFullScreen()
        if sys.platform == 'darwin':
            self.ui.main_widget.window().setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            self.ui.main_widget.window().show()

    def exit_fullscreen(self):
        """Exit fullscreen mode"""
        self.ui.main_widget.window().showNormal()
        if sys.platform == 'darwin':
            self.ui.main_widget.window().setWindowFlags(Qt.Window)
            self.ui.main_widget.window().show()

    def connect_to_server(self):
        """Connect to video server"""
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
        """Disconnect from server"""
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

    def _perform_login(self, username, password):
        """Internal method to perform login with credentials"""
        try:
            self.is_authenticated = self.network.login(username, password)
            self.ui.set_auth_state(self.is_authenticated)

            if self.is_authenticated:
                self.username = username
                self.ui.status_label.setText("Авторизация успешна")
                self.load_video_list()
                self.load_user_videos()
                self.load_user_channels()
                self.ui.account_btn.setEnabled(True)
                self.ui.channel_btn.setEnabled(True)
            else:
                self.ui.status_label.setText("Неверные данные для входа")

        except Exception as e:
            self.ui.status_label.setText(f"Ошибка авторизации: {str(e)}")
            logger.error(f"Auth error: {str(e)}")

    def handle_auth(self):
        """Handle user authentication"""
        if self.is_authenticated:
            self.logout()
            return

        if not self.network.is_connected():
            self.ui.status_label.setText("Сначала подключитесь к серверу")
            return

        login_dialog = LoginDialog(self.ui.main_widget)
        if login_dialog.exec_() == QDialog.Accepted:
            username, password = login_dialog.get_credentials()
            self._perform_login(username, password)

    def logout(self):
        """Logout current user"""
        self.is_authenticated = False
        self.username = None
        self.ui.set_auth_state(False)
        self.ui.status_label.setText("Вы вышли из системы")
        self.network.token = None
        self.ui.account_btn.setEnabled(False)
        self.ui.channel_btn.setEnabled(False)

    def handle_register(self):
        """Handle user registration"""
        if not self.network.is_connected():
            self.ui.status_label.setText("Сначала подключитесь к серверу")
            return

        register_dialog = RegisterDialog(self.ui.main_widget)
        if register_dialog.exec_() == QDialog.Accepted:
            username, password = register_dialog.get_credentials()
            try:
                success = self.network.register(username, password)
                if success:
                    self.ui.status_label.setText("Регистрация успешна. Выполняется вход...")
                    self._perform_login(username, password)
                else:
                    self.ui.status_label.setText("Ошибка регистрации (возможно, имя уже занято)")
            except Exception as e:
                self.ui.status_label.setText(f"Ошибка регистрации: {str(e)}")
                logger.error(f"Registration error: {str(e)}")

    def show_user_account(self):
        """Show user account dialog"""
        if not self.is_authenticated:
            return

        dialog = UserAccountDialog(self.ui.main_widget)

        # Загружаем каналы пользователя
        try:
            user_channels = self.network.get_user_channels_by_user(self.username)
            dialog.set_channels(user_channels)
        except Exception as e:
            logger.error(f"Error loading user channels: {str(e)}")
            QMessageBox.warning(self.ui.main_widget, "Ошибка", "Не удалось загрузить каналы пользователя")

        dialog.set_videos(self.user_videos)
        if dialog.exec_() == QDialog.Accepted:
            selected_video = dialog.get_selected_video()
            if selected_video:
                self.current_video_id, video_info = selected_video
                self.segment_length = video_info.segment_length
                self.total_segments = video_info.segment_amount
                self.ui.play_btn.setEnabled(True)
                self.update_video_info(video_info)

    def show_channels(self):
        """Show channels dialog"""
        if not self.is_authenticated:
            QMessageBox.warning(self.ui.main_widget, "Ошибка", "Необходимо авторизоваться")
            return

        dialog = ChannelDialog(self.ui.main_widget)
        dialog.exec_()

    def handle_channel_double_click(self, item):
        """Handle double click on channel item"""
        channel_id = item.data(Qt.UserRole)
        channel_info = self.network.get_channel_info(channel_id)
        if channel_info:
            info_dialog = ChannelInfoDialog(self.ui.main_widget)
            info_dialog.set_channel_info(channel_info)
            info_dialog.exec_()

    def create_channel(self):
        """Create new channel"""
        if not self.is_authenticated:
            QMessageBox.warning(self.ui.main_widget, "Ошибка", "Необходимо авторизоваться")
            return

        dialog = CreateChannelDialog(self.ui.main_widget)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_channel_info()
            try:
                channel_id = self.network.create_channel(name, description)
                if channel_id:
                    QMessageBox.information(self.ui.main_widget, "Успех",
                                          f"Канал '{name}' создан (ID: {channel_id})")
                    self.load_user_channels()
                else:
                    QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                       "Не удалось создать канал")
            except Exception as e:
                QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                   f"Ошибка при создании канала: {str(e)}")
                logger.error(f"Create channel error: {str(e)}")

    def load_video_list(self):
        """Load list of available videos"""
        try:
            self.video_list = self.network.get_video_list()
            if self.video_list:
                self.ui.video_list_widget.clear()
                for video_id, video_info in self.video_list:
                    self.ui.video_list_widget.addItem(f"{video_id}: {video_info.title}")
        except Exception as e:
            logger.error(f"Ошибка загрузки списка видео: {str(e)}")
            QMessageBox.critical(self.ui.main_widget, "Ошибка",
                               f"Не удалось загрузить список видео: {str(e)}")

    def load_user_videos(self):
        """Load user's videos"""
        if not self.is_authenticated:
            return

        try:
            self.user_videos = self.network.get_user_videos()
        except Exception as e:
            logger.error(f"Ошибка загрузки пользовательских видео: {str(e)}")
            self.user_videos = []

    def load_user_channels(self):
        """Load user's channels"""
        if not self.is_authenticated:
            return

        try:
            self.channels = self.network.get_user_channels()
        except Exception as e:
            logger.error(f"Ошибка загрузки каналов пользователя: {str(e)}")
            self.channels = []

    def load_channel_videos(self, channel_id):
        """Load videos for specific channel"""
        try:
            video_ids = self.network.get_channel_videos(channel_id)
            if video_ids:
                self.ui.video_list_widget.clear()
                for video_id in video_ids:
                    video_info = self.network.get_video_info(video_id)
                    if video_info:
                        self.ui.video_list_widget.addItem(f"{video_id}: {video_info.title}")
        except Exception as e:
            logger.error(f"Ошибка загрузки видео канала: {str(e)}")
            QMessageBox.critical(self.ui.main_widget, "Ошибка",
                               f"Не удалось загрузить видео канала: {str(e)}")

    def select_video(self, item):
        """Handle video selection from list"""
        index = self.ui.video_list_widget.row(item)
        if index < len(self.video_list):
            self.current_video_id, video_info = self.video_list[index]
            self.segment_length = video_info.segment_length
            self.total_segments = video_info.segment_amount
            self.ui.play_btn.setEnabled(True)
            self.update_video_info(video_info)

    def update_video_info(self, video_info):
        """Update video info display"""
        duration = self.format_duration(video_info.segment_amount * video_info.segment_length)
        self.ui.video_info_label.setText(
            f"Название: {video_info.title}\n"
            f"Автор: {video_info.author}\n"
            f"Канал: {video_info.channel_id}\n"
            f"Длительность: {duration}\n"
            f"Описание: {video_info.description}"
        )

    def format_duration(self, seconds):
        """Format duration in seconds to HH:MM:SS"""
        return str(timedelta(seconds=seconds))

    def play_video(self):
        """Start video playback"""
        if not self.current_video_id:
            return

        try:
            self.current_segment = 0
            segment_data = self.network.get_video_segment(
                self.current_video_id,
                self.current_segment,
                1  # Quality level
            )

            if segment_data:
                # Set total duration for the slider
                total_duration = self.total_segments * self.segment_length * 1000
                self.ui.progress_slider.setMaximum(total_duration)

                self.media_player.play_segment(segment_data, self.current_segment)
                self.ui.play_btn.setEnabled(False)
                self.ui.pause_btn.setEnabled(True)
                self.ui.stop_btn.setEnabled(True)
                self.ui.status_label.setText(
                    f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")

                # Preload next segment
                if self.total_segments > 1:
                    self.media_player.buffer_next_segment(
                        self.current_video_id,
                        self.current_segment + 1,
                        1,
                        self.total_segments
                    )
        except Exception as e:
            logger.error(f"Play video error: {str(e)}")

    def handle_media_status(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.EndOfMedia:
            self.current_segment += 1
            if self.current_segment < self.total_segments:
                # Play next segment
                segment_data = self.network.get_video_segment(
                    self.current_video_id,
                    self.current_segment,
                    1
                )

                if segment_data:
                    self.media_player.play_segment(segment_data, self.current_segment)
                    self.ui.status_label.setText(
                        f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")

                    # Preload next segment if available
                    if self.current_segment + 1 < self.total_segments:
                        self.media_player.buffer_next_segment(
                            self.current_video_id,
                            self.current_segment + 1,
                            1,
                            self.total_segments
                        )
            else:
                self.stop_video()

    def update_position(self, position=None):
        """Update playback position display"""
        if position is None:
            position = self.media_player.position()

        # Calculate total position across all segments
        total_ms = (self.current_segment * self.segment_length * 1000) + position
        total_duration = self.total_segments * self.segment_length * 1000

        # Update slider with total position
        self.ui.progress_slider.setMaximum(total_duration)
        self.ui.progress_slider.setValue(total_ms)

        # Update time labels
        total_seconds = total_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        self.ui.current_time.setText(f"{minutes:02d}:{seconds:02d}")

        total_duration_seconds = total_duration // 1000
        dur_minutes = total_duration_seconds // 60
        dur_seconds = total_duration_seconds % 60
        self.ui.duration.setText(f"{dur_minutes:02d}:{dur_seconds:02d}")

    def seek_video(self, position):
        """Seek to specific position in video"""
        segment_ms = self.segment_length * 1000
        new_segment = position // segment_ms
        segment_pos = position % segment_ms

        if new_segment >= self.total_segments:
            return  # Don't seek beyond the end

        if new_segment != self.current_segment:
            self.current_segment = new_segment
            segment_data = self.network.get_video_segment(
                self.current_video_id,
                self.current_segment,
                1
            )

            if segment_data:
                self.media_player.play_segment(segment_data, self.current_segment)
                self.media_player.media_player.setPosition(segment_pos)
                self.ui.status_label.setText(
                    f"Воспроизведение: сегмент {self.current_segment + 1}/{self.total_segments}")

                # Preload next segment if available
                if self.current_segment + 1 < self.total_segments:
                    self.media_player.buffer_next_segment(
                        self.current_video_id,
                        self.current_segment + 1,
                        1,
                        self.total_segments
                    )
        else:
            self.media_player.media_player.setPosition(segment_pos)

    def pause_video(self):
        """Pause video playback"""
        self.media_player.pause()
        self.ui.play_btn.setEnabled(True)
        self.ui.pause_btn.setEnabled(False)

    def stop_video(self):
        """Stop video playback"""
        self.media_player.stop_playback()
        self.ui.progress_slider.setValue(0)
        self.ui.current_time.setText("00:00")
        self.ui.duration.setText("00:00")
        self.current_segment = 0
        self.ui.play_btn.setEnabled(True)
        self.ui.pause_btn.setEnabled(False)
        self.ui.stop_btn.setEnabled(False)

    def on_player_state_changed(self, state):
        """Handle player state changes"""
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

    def handle_video_upload(self, video_info):
        """Handle video upload"""
        try:
            if not hasattr(video_info, 'file_path') or not video_info.file_path:
                QMessageBox.warning(self.ui.main_widget, "Ошибка", "Файл не выбран")
                return

            if not os.path.exists(video_info.file_path):
                QMessageBox.warning(self.ui.main_widget, "Ошибка", "Выбранный файл не существует")
                return

            progress_dialog = QProgressDialog(
                "Загрузка видео...", "Отмена", 0, 100, self.ui.main_widget)
            progress_dialog.setWindowTitle("Загрузка")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.show()

            def upload_callback(progress):
                progress_dialog.setValue(progress)
                QApplication.processEvents()
                return not progress_dialog.wasCanceled()

            video_id = self.network.upload_video(
                self.current_channel_id,
                video_info.title,
                video_info.description,
                video_info.file_path,
                upload_callback
            )
            progress_dialog.close()

            if video_id:
                QMessageBox.information(
                    self.ui.main_widget, "Успех",
                    f"Видео '{video_info.title}' успешно загружено (ID: {video_id})")
                self.load_user_videos()
                self.load_video_list()
            else:
                QMessageBox.critical(
                    self.ui.main_widget, "Ошибка",
                    "Загрузка отменена или произошла ошибка")

        except Exception as e:
            QMessageBox.critical(
                self.ui.main_widget, "Ошибка",
                f"Не удалось загрузить видео: {str(e)}")
            logger.error(f"Upload error: {str(e)}", exc_info=True)

    def edit_video_info(self, video_id, title, description):
        """Edit video information"""
        try:
            if not title.strip():
                QMessageBox.warning(self.ui.main_widget, "Ошибка", "Название не может быть пустым")
                return False

            success = self.network.edit_video(video_id, title, description)
            if success:
                QMessageBox.information(self.ui.main_widget, "Успех",
                                      "Информация о видео обновлена")
                self.load_user_videos()
                self.load_video_list()
                return True
            else:
                QMessageBox.critical(self.ui.main_widget, "Ошибка",
                                   "Не удалось обновить информацию о видео")
                return False
        except Exception as e:
            QMessageBox.critical(self.ui.main_widget, "Ошибка",
                               f"Ошибка при обновлении видео: {str(e)}")
            logger.error(f"Edit video error: {str(e)}")
            return False