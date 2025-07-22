from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QPushButton,
                             QSlider, QLabel, QListWidget, QDialog,
                             QDialogButtonBox, QFrame, QLineEdit, QFormLayout,
                             QScrollArea, QListWidgetItem, QMessageBox,
                             QComboBox, QProgressBar, QToolButton, QFileDialog,
                             QTextEdit)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPalette, QColor, QIcon, QFont
import os


class DarkPalette(QPalette):
    def __init__(self):
        super().__init__()
        self.setColor(QPalette.Window, QColor(53, 53, 53))
        self.setColor(QPalette.WindowText, Qt.white)
        self.setColor(QPalette.Base, QColor(25, 25, 25))
        self.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        self.setColor(QPalette.ToolTipBase, Qt.white)
        self.setColor(QPalette.ToolTipText, Qt.white)
        self.setColor(QPalette.Text, Qt.white)
        self.setColor(QPalette.Button, QColor(53, 53, 53))
        self.setColor(QPalette.ButtonText, Qt.white)
        self.setColor(QPalette.BrightText, Qt.red)
        self.setColor(QPalette.Link, QColor(42, 130, 218))
        self.setColor(QPalette.Highlight, QColor(42, 130, 218))
        self.setColor(QPalette.HighlightedText, Qt.black)


class VideoPlayerUI:
    def __init__(self):
        self.main_widget = QWidget()
        self.setup_ui()
        self.apply_dark_theme()

    def apply_dark_theme(self):
        palette = DarkPalette()
        self.main_widget.setPalette(palette)

        self.main_widget.setStyleSheet("""
            QWidget {
                background-color: #353535;
                color: white;
                font-family: Arial;
                font-size: 12px;
            }
            QPushButton {
                background-color: #454545;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #252525;
            }
            QPushButton:disabled {
                color: #777;
            }
            QLineEdit, QComboBox {
                background-color: #252525;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #444;
            }
            QSlider::handle:horizontal {
                width: 14px;
                height: 14px;
                margin: -5px 0;
                background: white;
                border-radius: 7px;
            }
            QLabel {
                color: white;
            }
            QListWidget {
                background-color: #252525;
                border: 1px solid #444;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #2a82da;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2a82da;
            }
        """)

    def setup_ui(self):
        self.main_widget.setMinimumSize(1000, 700)
        main_layout = QVBoxLayout(self.main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Connection panel
        connection_panel = QWidget()
        connection_layout = QHBoxLayout(connection_panel)

        self.server_input = QLineEdit("localhost:12345")
        self.connect_btn = QPushButton("Подключиться")
        self.disconnect_btn = QPushButton("Отключиться")
        self.login_btn = QPushButton("Войти")
        self.register_btn = QPushButton("Регистрация")
        self.account_btn = QPushButton("Мой аккаунт")

        self.disconnect_btn.setEnabled(False)
        self.login_btn.setEnabled(False)
        self.account_btn.setEnabled(False)

        connection_layout.addWidget(QLabel("Сервер:"))
        connection_layout.addWidget(self.server_input)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        connection_layout.addWidget(self.login_btn)
        connection_layout.addWidget(self.register_btn)
        connection_layout.addWidget(self.account_btn)
        connection_layout.addStretch()

        main_layout.addWidget(connection_panel)

        # Video player area
        player_panel = QWidget()
        player_layout = QVBoxLayout(player_panel)

        self.video_widget = QWidget()
        self.video_widget.setLayout(QVBoxLayout())
        self.video_widget.setMinimumHeight(400)
        player_layout.addWidget(self.video_widget, stretch=1)

        self.video_info_label = QLabel("Выберите видео из списка")
        player_layout.addWidget(self.video_info_label)

        # Controls
        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("⏸")
        self.stop_btn = QPushButton("⏹")

        self.progress_slider = QSlider(Qt.Horizontal)
        self.current_time = QLabel("00:00")
        self.duration = QLabel("00:00")

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.progress_slider)
        controls_layout.addWidget(self.current_time)
        controls_layout.addWidget(QLabel("/"))
        controls_layout.addWidget(self.duration)

        player_layout.addLayout(controls_layout)
        main_layout.addWidget(player_panel, stretch=1)

        # Video list
        video_list_panel = QWidget()
        video_list_layout = QVBoxLayout(video_list_panel)

        self.video_list_label = QLabel("Доступные видео")
        video_list_layout.addWidget(self.video_list_label)

        self.video_list_widget = QListWidget()
        self.video_list_widget.setFlow(QListWidget.LeftToRight)
        self.video_list_widget.setWrapping(False)
        self.video_list_widget.setFixedHeight(120)
        video_list_layout.addWidget(self.video_list_widget)

        main_layout.addWidget(video_list_panel)

        # Status bar
        self.status_label = QLabel("Готов к подключению")
        main_layout.addWidget(self.status_label)

    def set_auth_state(self, authenticated):
        """Обновляет состояние элементов интерфейса при авторизации/выходе"""
        self.login_btn.setEnabled(True)
        self.register_btn.setEnabled(not authenticated)
        self.account_btn.setEnabled(authenticated)
        if authenticated:
            self.login_btn.setText("Выйти")
            self.video_list_label.setText("Доступные видео (авторизован)")
        else:
            self.login_btn.setText("Войти")
            self.video_list_label.setText("Доступные видео")


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Авторизация")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)

    def get_credentials(self):
        return self.username_input.text(), self.password_input.text()


class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Регистрация")
        self.setFixedSize(300, 250)

        layout = QVBoxLayout(self)

        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)

        form_layout.addRow("Логин:", self.username_input)
        form_layout.addRow("Пароль:", self.password_input)
        form_layout.addRow("Подтверждение:", self.confirm_password_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(buttons)

    def validate(self):
        if self.password_input.text() != self.confirm_password_input.text():
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return
        if len(self.username_input.text()) < 3:
            QMessageBox.warning(self, "Ошибка", "Логин должен быть не менее 3 символов")
            return
        if len(self.password_input.text()) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
            return
        self.accept()

    def get_credentials(self):
        return self.username_input.text(), self.password_input.text()


class UserAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Мой аккаунт")
        self.setFixedSize(500, 400)
        self.parent_widget = parent  # Сохраняем ссылку на родительский виджет

        layout = QVBoxLayout(self)

        # Buttons panel
        buttons_panel = QWidget()
        buttons_layout = QHBoxLayout(buttons_panel)

        self.upload_btn = QPushButton("Загрузить видео")
        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.setEnabled(False)

        buttons_layout.addWidget(self.upload_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_panel)

        self.video_list = QListWidget()
        self.video_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.video_list, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect signals
        self.upload_btn.clicked.connect(self.show_upload_dialog)
        self.edit_btn.clicked.connect(self.show_edit_dialog)

    def on_selection_changed(self):
        self.edit_btn.setEnabled(len(self.video_list.selectedItems()) > 0)

    def show_upload_dialog(self):
        upload_dialog = UploadDialog(self)
        if upload_dialog.exec_() == QDialog.Accepted:
            if hasattr(self.parent_widget, 'handle_video_upload'):
                self.parent_widget.handle_video_upload(upload_dialog.get_video_info())

    def show_edit_dialog(self):
        selected = self.video_list.selectedItems()
        if not selected:
            return

        video_id, video_info = selected[0].data(Qt.UserRole)
        edit_dialog = EditVideoDialog(self, video_info.title, video_info.description)
        if edit_dialog.exec_() == QDialog.Accepted:
            new_title, new_description = edit_dialog.get_video_info()
            if hasattr(self.parent_widget, 'edit_video_info'):
                self.parent_widget.edit_video_info(video_id, new_title, new_description)

    def set_videos(self, videos):
        self.video_list.clear()
        for video_id, video_info in videos:
            item = QListWidgetItem(f"{video_id}: {video_info.title}")
            item.setData(Qt.UserRole, (video_id, video_info))
            self.video_list.addItem(item)

    def get_selected_video(self):
        selected_items = self.video_list.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
        return None


class UploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузить видео")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название видео")

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Описание видео")
        self.desc_edit.setMaximumHeight(80)

        self.file_button = QPushButton("Выбрать файл")
        self.file_button.clicked.connect(self.select_file)
        self.file_label = QLabel("Файл не выбран")

        form.addRow("Название:", self.title_edit)
        form.addRow("Описание:", self.desc_edit)
        form.addRow("Видеофайл:", self.file_button)
        form.addRow("", self.file_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def select_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видеофайл",
            "",
            "Видео (*.mp4 *.avi *.mov)"
        )
        if file:
            self.file_label.setText(os.path.basename(file))
            self.file_path = file

    def validate(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название видео")
            return
        if not hasattr(self, 'file_path'):
            QMessageBox.warning(self, "Ошибка", "Выберите видеофайл")
            return
        self.accept()

    def get_video_info(self):
        return type('VideoInfo', (), {
            'title': self.title_edit.text(),
            'description': self.desc_edit.toPlainText(),
            'file_path': self.file_path
        })


class EditVideoDialog(QDialog):
    def __init__(self, parent=None, title="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Редактировать видео")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Название видео")

        self.desc_edit = QTextEdit(description)
        self.desc_edit.setPlaceholderText("Описание видео")
        self.desc_edit.setMaximumHeight(80)

        form.addRow("Название:", self.title_edit)
        form.addRow("Описание:", self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def validate(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название видео")
            return
        self.accept()

    def get_video_info(self):
        return self.title_edit.text(), self.desc_edit.toPlainText()