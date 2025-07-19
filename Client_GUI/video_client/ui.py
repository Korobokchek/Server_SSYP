from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QPushButton,
                             QSlider, QLabel, QListWidget, QDialog,
                             QDialogButtonBox, QFrame, QLineEdit, QFormLayout)
from PyQt5.QtCore import Qt


class VideoPlayerUI:
    def __init__(self):
        self.main_widget = None
        self.setup_ui()

    def setup_ui(self):
        self.main_widget = QWidget()
        self.main_widget.setMinimumSize(1000, 600)

        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Connection panel
        self._setup_connection_panel(main_layout)

        # Content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # Left panel (video list)
        self._setup_video_list_panel(content_layout)

        # Right panel (player)
        self._setup_player_panel(content_layout)

        main_layout.addWidget(content_widget)

        # Status label
        self.status_label = QLabel("Готов к подключению")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

    def _setup_connection_panel(self, parent_layout):
        panel = QFrame()
        panel.setStyleSheet("background-color: #f8f8f8; border-radius: 8px; padding: 10px;")

        layout = QHBoxLayout(panel)
        layout.setSpacing(10)

        self.server_input = QLineEdit("localhost:12345")
        self.server_input.setMinimumWidth(200)

        self.connect_btn = QPushButton("Подключиться")
        self.disconnect_btn = QPushButton("Отключиться")
        self.login_btn = QPushButton("Войти")

        btn_style = """
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #dddddd;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 100px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:disabled {
                color: #aaaaaa;
            }
        """

        self.connect_btn.setStyleSheet(btn_style)
        self.disconnect_btn.setStyleSheet(btn_style)
        self.login_btn.setStyleSheet(btn_style)
        self.disconnect_btn.setEnabled(False)
        self.login_btn.setEnabled(False)

        layout.addWidget(QLabel("Сервер:"))
        layout.addWidget(self.server_input)
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.disconnect_btn)
        layout.addWidget(self.login_btn)

        parent_layout.addWidget(panel)

    def _setup_video_list_panel(self, parent_layout):
        panel = QFrame()
        panel.setStyleSheet("background-color: #ffffff; border-radius: 8px;")
        panel.setMinimumWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.video_list_label = QLabel("Доступные видео")
        layout.addWidget(self.video_list_label)

        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #dddddd;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #f0f0f0;
            }
        """)

        self.video_info_label = QLabel("Выберите видео из списка")
        self.video_info_label.setWordWrap(True)

        layout.addWidget(self.video_list_widget)
        layout.addWidget(self.video_info_label)
        parent_layout.addWidget(panel)

    def _setup_player_panel(self, parent_layout):
        panel = QFrame()
        panel.setStyleSheet("background-color: #ffffff; border-radius: 8px;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Video widget container
        self.video_widget = QWidget()
        self.video_widget.setLayout(QVBoxLayout())
        self.video_widget.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.video_widget)

        # Controls
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("⏸")
        self.stop_btn = QPushButton("⏹")

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        layout.addLayout(controls_layout)

        # Progress bar
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #e0e0e0;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: #555555;
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.progress_slider)

        # Time labels
        time_layout = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.duration = QLabel("00:00")

        time_layout.addWidget(self.current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.duration)

        layout.addLayout(time_layout)
        parent_layout.addWidget(panel, stretch=1)

    def set_connection_state(self, connected):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.login_btn.setEnabled(connected)

    def set_auth_state(self, authenticated):
        self.login_btn.setText("Выйти" if authenticated else "Войти")


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Введите логин")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.button(QDialogButtonBox.Ok).setText("Войти")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")

        layout.addLayout(form_layout)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def get_credentials(self):
        return (self.username_input.text(), self.password_input.text())