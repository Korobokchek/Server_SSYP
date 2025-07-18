from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
                             QSlider, QLabel, QListWidget, QLineEdit)
from PyQt5.QtCore import Qt
from .logger import logger


class VideoPlayerUI:
    def __init__(self):
        """Инициализация пользовательского интерфейса видеоплеера"""
        # Инициализация всех виджетов как None
        self.main_widget = None  # Главный виджет-контейнер
        self.connect_btn = None  # Кнопка подключения к серверу
        self.disconnect_btn = None # Кнопка отключения от сервера
        self.server_input = None  # Поле ввода адреса сервера
        self.video_list_widget = None  # Список доступных видео
        self.video_info_label = None  # Метка с информацией о видео
        self.play_btn = None  # Кнопка воспроизведения
        self.pause_btn = None  # Кнопка паузы
        self.stop_btn = None  # Кнопка остановки
        self.progress_slider = None  # Слайдер прогресса воспроизведения
        self.time_label = None  # Метка с временем воспроизведения
        self.video_list_label = None  # Новая метка для заголовка списка видео

        self.setup_ui()  # Настройка интерфейса
        logger.info("UI initialized")  # Логирование инициализации

    def setup_ui(self):
        """Создание и компоновка всех элементов интерфейса"""
        try:
            # Создаем главный виджет и основной макет
            self.main_widget = QWidget()
            self.layout = QVBoxLayout()  # Вертикальный макет

            # 1. Панель подключения к серверу
            self.connection_layout = QHBoxLayout()  # Горизонтальный макет
            self.server_input = QLineEdit("localhost:12345")  # Поле ввода адреса
            self.connect_btn = QPushButton("Подключиться")  # Кнопка подключения
            self.disconnect_btn = QPushButton("Отключиться")
            self.connection_layout.addWidget(self.server_input)
            self.connection_layout.addWidget(self.connect_btn)
            self.connection_layout.addWidget(self.disconnect_btn)

            # 2. Заголовок списка видео (новая строка)
            self.video_list_label = QLabel("Доступные видео:")
            self.video_list_label.setStyleSheet("font-weight: bold;")

            # 3. Список доступных видео
            self.video_list_widget = QListWidget()  # Виджет списка
            self.video_list_widget.setMinimumHeight(150)  # Минимальная высота

            # 4. Информация о выбранном видео
            self.video_info_label = QLabel("Выберите видео из списка")
            self.video_info_label.setWordWrap(True)  # Перенос текста
            self.video_info_label.setStyleSheet("padding: 5px;")

            # 5. Элементы управления плеером
            self.control_layout = QHBoxLayout()
            self.play_btn = QPushButton("Воспроизвести")
            self.pause_btn = QPushButton("Пауза")
            self.stop_btn = QPushButton("Стоп")

            # Добавляем кнопки в горизонтальный макет
            self.control_layout.addWidget(self.play_btn)
            self.control_layout.addWidget(self.pause_btn)
            self.control_layout.addWidget(self.stop_btn)

            # 6. Слайдер прогресса воспроизведения
            self.progress_slider = QSlider(Qt.Horizontal)  # Горизонтальный слайдер
            self.progress_slider.setMinimum(0)

            # 7. Метка времени (текущее/общее)
            self.time_label = QLabel("00:00 / 00:00")
            self.time_label.setAlignment(Qt.AlignCenter)  # Выравнивание по центру




            # Сборка интерфейса (добавление всех элементов в основной макет)
            self.layout.addLayout(self.connection_layout)  # Панель подключения
            self.layout.addWidget(self.video_list_label)  # Заголовок списка
            self.layout.addWidget(self.video_list_widget)  # Сам список видео
            self.layout.addWidget(self.video_info_label)  # Информация о видео
            self.layout.addWidget(self.progress_slider)  # Слайдер прогресса
            self.layout.addWidget(self.time_label)  # Временная метка
            self.layout.addLayout(self.control_layout)  # Панель управления




            # Установка основного макета для главного виджета
            self.main_widget.setLayout(self.layout)
            logger.debug("UI setup completed")  # Логирование успешной настройки

        except Exception as e:
            logger.critical(f"Failed to setup UI: {str(e)}")  # Логирование ошибок
            raise  # Повторно вызываем исключение

    def update_controls(self, state):
        """
        Обновление состояния кнопок управления в зависимости от состояния плеера
        :param state: Текущее состояние медиаплеера (Playing, Paused, Stopped)
        """
        from PyQt5.QtMultimedia import QMediaPlayer
        # Воспроизведение доступно, если плеер не в состоянии Playing
        self.play_btn.setEnabled(state != QMediaPlayer.PlayingState)
        # Пауза доступна только при воспроизведении
        self.pause_btn.setEnabled(state == QMediaPlayer.PlayingState)
        # Стоп доступен, если плеер не в состоянии Stopped
        self.stop_btn.setEnabled(state != QMediaPlayer.StoppedState)
        logger.debug(f"Updated controls for state: {state}")

    def update_time(self, current_time, duration):
        """
        Обновление временных меток
        :param current_time: Текущая позиция в миллисекундах
        :param duration: Общая длительность в миллисекундах
        """
        # Форматирование времени в MM:SS
        time_str = (f"{int(current_time // 60000):02d}:{int((current_time % 60000) / 1000):02d} / "
                    f"{int(duration // 60000):02d}:{int((duration % 60000) / 1000):02d}")
        self.time_label.setText(time_str)
        logger.debug(f"Updated time display: {time_str}")