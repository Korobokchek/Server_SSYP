from PyQt5.QtWidgets import (QHBoxLayout, QVBoxLayout, QWidget, QPushButton,
                            QSlider, QLabel, QListWidget, QDialog,
                            QDialogButtonBox, QFrame, QLineEdit, QFormLayout,
                            QScrollArea, QListWidgetItem, QMessageBox,
                            QComboBox, QProgressBar, QToolButton, QFileDialog,
                            QTextEdit, QProgressDialog, QCheckBox, QTabWidget)
from PyQt5.QtCore import Qt, QSize, QCoreApplication
from PyQt5.QtGui import QPalette, QColor, QIcon, QFont
import os
import logging

logger = logging.getLogger(__name__)

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
        self.is_authenticated = False
        self.network = Network()

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
            QTabWidget::pane {
                border: 1px solid #444;
            }
            QTabBar::tab {
                background: #353535;
                padding: 5px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background: #454545;
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

        self.server_input = QLineEdit("localhost:8080")
        self.connect_btn = QPushButton("Подключиться")
        self.disconnect_btn = QPushButton("Отключиться")
        self.login_btn = QPushButton("Войти")
        self.register_btn = QPushButton("Регистрация")
        self.account_btn = QPushButton("Мой аккаунт")
        self.channel_btn = QPushButton("Каналы")

        self.disconnect_btn.setEnabled(False)
        self.login_btn.setEnabled(False)
        self.account_btn.setEnabled(False)
        self.channel_btn.setEnabled(False)

        connection_layout.addWidget(QLabel("Сервер:"))
        connection_layout.addWidget(self.server_input)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.disconnect_btn)
        connection_layout.addWidget(self.login_btn)
        connection_layout.addWidget(self.register_btn)
        connection_layout.addWidget(self.account_btn)
        connection_layout.addWidget(self.channel_btn)
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
        self.video_list_widget.setFixedHeight(75)
        video_list_layout.addWidget(self.video_list_widget)

        main_layout.addWidget(video_list_panel)

        # Status bar
        self.status_label = QLabel("Готов к подключению")
        main_layout.addWidget(self.status_label)

    def set_auth_state(self, authenticated):
        """Update UI elements based on authentication state"""
        self.is_authenticated = authenticated
        self.login_btn.setEnabled(True)
        self.register_btn.setEnabled(not authenticated)
        self.account_btn.setEnabled(authenticated)
        self.channel_btn.setEnabled(authenticated)
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
        self.setFixedSize(600, 500)
        self.parent_widget = parent

        layout = QVBoxLayout(self)

        # Создаем вкладки
        self.tabs = QTabWidget()

        # Вкладка с видео
        self.video_tab = QWidget()
        self.setup_video_tab()
        self.tabs.addTab(self.video_tab, "Мои видео")

        # Вкладка с каналами
        self.channel_tab = QWidget()
        self.setup_channel_tab()
        self.tabs.addTab(self.channel_tab, "Мои каналы")

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def setup_video_tab(self):
        layout = QVBoxLayout(self.video_tab)

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
        self.video_list.itemSelectionChanged.connect(self.on_video_selection_changed)
        layout.addWidget(self.video_list, stretch=1)

        # Connect signals
        self.upload_btn.clicked.connect(self.handle_upload)
        self.edit_btn.clicked.connect(self.handle_edit)

    def setup_channel_tab(self):
        layout = QVBoxLayout(self.channel_tab)

        # Buttons panel
        buttons_panel = QWidget()
        buttons_layout = QHBoxLayout(buttons_panel)

        self.create_channel_btn = QPushButton("Создать канал")
        self.channel_info_btn = QPushButton("Информация")
        self.channel_info_btn.setEnabled(False)

        buttons_layout.addWidget(self.create_channel_btn)
        buttons_layout.addWidget(self.channel_info_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_panel)

        self.channel_list = QListWidget()
        self.channel_list.itemSelectionChanged.connect(self.on_channel_selection_changed)
        self.channel_list.itemDoubleClicked.connect(self.on_channel_double_click)
        layout.addWidget(self.channel_list, stretch=1)

        # Connect signals
        self.create_channel_btn.clicked.connect(self.handle_create_channel)
        self.channel_info_btn.clicked.connect(self.handle_channel_info)

    def on_video_selection_changed(self):
        self.edit_btn.setEnabled(len(self.video_list.selectedItems()) > 0)

    def on_channel_selection_changed(self):
        self.channel_info_btn.setEnabled(len(self.channel_list.selectedItems()) > 0)

    def on_channel_double_click(self, item):
        channel_id = item.data(Qt.UserRole)
        if hasattr(self.parent_widget, 'load_channel_videos'):
            self.parent_widget.load_channel_videos(channel_id)
        self.accept()

    def handle_upload(self):
        """Handle video upload by delegating to parent widget"""
        if hasattr(self.parent_widget, 'handle_video_upload'):
            upload_dialog = UploadDialog(self)
            if upload_dialog.exec_() == QDialog.Accepted:
                video_info = upload_dialog.get_video_info()
                self.parent_widget.handle_video_upload(video_info)

    def handle_edit(self):
        """Handle video editing by delegating to parent widget"""
        selected = self.video_list.selectedItems()
        if not selected:
            return

        if hasattr(self.parent_widget, 'edit_video_info'):
            video_id = selected[0].data(Qt.UserRole)
            video_info = selected[0].data(Qt.UserRole + 1)  # Assuming video_info is stored as additional data

            edit_dialog = EditVideoDialog(self, video_info.title, video_info.description)
            if edit_dialog.exec_() == QDialog.Accepted:
                title, description = edit_dialog.get_video_info()
                self.parent_widget.edit_video_info(video_id, title, description)

    def handle_create_channel(self):
        """Handle channel creation by delegating to parent widget"""
        if hasattr(self.parent_widget, 'create_channel'):
            self.parent_widget.create_channel()

    def handle_channel_info(self):
        """Handle channel info display by delegating to parent widget"""
        selected = self.channel_list.selectedItems()
        if not selected:
            return

        channel_id = selected[0].data(Qt.UserRole)
        if hasattr(self.parent_widget, 'show_channel_info'):
            self.parent_widget.show_channel_info(channel_id)

    def set_videos(self, videos):
        """Set the list of user videos"""
        self.video_list.clear()
        for video_id, video_info in videos:
            item = QListWidgetItem(f"{video_id}: {video_info.title}")
            item.setData(Qt.UserRole, video_id)
            item.setData(Qt.UserRole + 1, video_info)  # Store video_info for editing
            self.video_list.addItem(item)

    def set_channels(self, channels):
        """Set the list of user channels"""
        self.channel_list.clear()
        for channel_id, channel_info in channels:
            item = QListWidgetItem(f"{channel_id}: {channel_info.name}")
            item.setData(Qt.UserRole, channel_id)
            self.channel_list.addItem(item)

    def get_selected_video(self):
        """Get the currently selected video"""
        selected_items = self.video_list.selectedItems()
        if selected_items:
            return (
                selected_items[0].data(Qt.UserRole),
                selected_items[0].data(Qt.UserRole + 1)  # video_info
            )
        return None

    def get_selected_channel(self):
        """Get the currently selected channel"""
        selected_items = self.channel_list.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
        return None

class ChannelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Каналы")
        self.setFixedSize(500, 400)
        self.parent_widget = parent

        layout = QVBoxLayout(self)

        # Buttons panel
        buttons_panel = QWidget()
        buttons_layout = QHBoxLayout(buttons_panel)

        self.create_btn = QPushButton("Создать канал")
        self.subscribe_btn = QPushButton("Подписаться")
        self.subscribe_btn.setEnabled(False)
        self.info_btn = QPushButton("Информация")
        self.info_btn.setEnabled(False)

        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.subscribe_btn)
        buttons_layout.addWidget(self.info_btn)
        buttons_layout.addStretch()

        layout.addWidget(buttons_panel)

        self.channel_list = QListWidget()
        self.channel_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.channel_list.itemDoubleClicked.connect(self.on_channel_double_click)
        layout.addWidget(self.channel_list, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect signals
        self.create_btn.clicked.connect(self.show_create_channel_dialog)
        self.subscribe_btn.clicked.connect(self.handle_subscription)
        self.info_btn.clicked.connect(self.show_channel_info)

    def on_selection_changed(self):
        has_selection = len(self.channel_list.selectedItems()) > 0
        self.subscribe_btn.setEnabled(has_selection)
        self.info_btn.setEnabled(has_selection)

    def on_channel_double_click(self, item):
        """Handle double click on channel item"""
        channel_id = item.data(Qt.UserRole)
        if hasattr(self.parent_widget, 'load_channel_videos'):
            self.parent_widget.load_channel_videos(channel_id)
        self.accept()

    def show_create_channel_dialog(self):
        if hasattr(self.parent_widget, 'create_channel'):
            self.parent_widget.create_channel()

    def show_channel_info(self):
        selected = self.channel_list.selectedItems()
        if not selected:
            return

        channel_id = selected[0].data(Qt.UserRole)
        if hasattr(self.parent_widget, 'show_channel_info'):
            self.parent_widget.show_channel_info(channel_id)

    def handle_subscription(self):
        selected = self.channel_list.selectedItems()
        if not selected:
            return

        channel_id = selected[0].data(Qt.UserRole)
        if hasattr(self.parent_widget, 'subscribe_to_channel'):
            self.parent_widget.subscribe_to_channel(channel_id)

    def set_channels(self, channels):
        self.channel_list.clear()
        for channel_id, channel_info in channels:
            item = QListWidgetItem(f"{channel_id}: {channel_info.name}")
            item.setData(Qt.UserRole, channel_id)
            self.channel_list.addItem(item)

    def get_selected_channel(self):
        selected_items = self.channel_list.selectedItems()
        if selected_items:
            return selected_items[0].data(Qt.UserRole)
        return None

class ChannelInfoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Информация о канале")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.stats_label = QLabel()

        layout.addWidget(self.name_label)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.stats_label)
        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def set_channel_info(self, channel_info):
        self.name_label.setText(channel_info.name)
        self.desc_label.setText(channel_info.description)
        self.stats_label.setText(
            f"Подписчики: {channel_info.subscribers}\n"
            f"Видео: {channel_info.video_amount}\n"
            f"Владелец: {'Вы' if channel_info.owner else 'Другой пользователь'}"
        )

class CreateChannelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать канал")
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название канала")

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Описание канала")
        self.desc_edit.setMaximumHeight(80)

        form.addRow("Название:", self.name_edit)
        form.addRow("Описание:", self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название канала")
            return
        self.accept()

    def get_channel_info(self):
        return self.name_edit.text().strip(), self.desc_edit.toPlainText().strip()

class UploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Загрузить видео")
        self.setFixedSize(500, 300)

        self.setup_ui()
        self.file_path = None

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Форма для ввода данных
        form = QFormLayout()

        # Поле для названия
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Введите название видео")
        form.addRow("Название:", self.title_edit)

        # Поле для описания
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Введите описание видео")
        self.desc_edit.setMaximumHeight(80)
        form.addRow("Описание:", self.desc_edit)

        # Выбор файла
        self.file_button = QPushButton("Выбрать файл")
        self.file_button.clicked.connect(self.select_file)
        self.file_label = QLabel("Файл не выбран")
        form.addRow("Видеофайл:", self.file_button)
        form.addRow("", self.file_label)

        # Настройки приватности
        self.public_check = QCheckBox("Сделать видео публичным")
        self.public_check.setChecked(True)
        form.addRow("Видимость:", self.public_check)

        # Кнопки OK/Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(buttons)

    def select_file(self):
        """Выбор видеофайла для загрузки"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видеофайл",
            "",
            "Видео (*.mp4 *.avi *.mov *.mkv);;Все файлы (*)"
        )

        if file:
            self.file_path = file
            self.file_label.setText(os.path.basename(file))

            # Автоматически заполняем название, если оно пустое
            if not self.title_edit.text().strip():
                base = os.path.splitext(os.path.basename(file))[0]
                self.title_edit.setText(base)

    def validate(self):
        """Проверка введенных данных перед отправкой"""
        errors = []

        if not self.title_edit.text().strip():
            errors.append("Введите название видео")

        if not self.file_path:
            errors.append("Выберите видеофайл")
        elif not os.path.exists(self.file_path):
            errors.append("Выбранный файл не существует")

        if errors:
            QMessageBox.warning(
                self,
                "Ошибка ввода",
                "\n".join(errors)
            )
        else:
            self.accept()

    def get_video_info(self):
        """Возвращает информацию о видео для загрузки"""
        class VideoInfo:
            def __init__(self, title, description, file_path, is_public):
                self.title = title
                self.description = description
                self.file_path = file_path
                self.is_public = is_public

        return VideoInfo(
            self.title_edit.text().strip(),
            self.desc_edit.toPlainText().strip(),
            self.file_path,
            self.public_check.isChecked()
        )

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
        return self.title_edit.text().strip(), self.desc_edit.toPlainText().strip()

class Network:
    """Mock network class for demonstration"""
    def create_channel(self, name, description):
        # In a real implementation, this would make a network request
        import random
        return random.randint(1, 1000)  # Return random ID for demo