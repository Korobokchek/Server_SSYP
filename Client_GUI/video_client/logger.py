import logging
from logging.handlers import RotatingFileHandler
import os
import sys

class VideoClientLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configure_logger()
        return cls._instance

    def _configure_logger(self):
        """Настройка системы логирования"""
        self.logger = logging.getLogger('VideoClient')
        self.logger.setLevel(logging.DEBUG)

        # Создаем папку для логов
        os.makedirs('logs', exist_ok=True)

        # Формат сообщений
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Файловый обработчик (до 5 файлов по 1MB каждый)
        file_handler = RotatingFileHandler(
            'logs/video_client.log',
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)

        # Консольный вывод
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Добавляем обработчики
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

# Глобальный доступ к логгеру
logger = VideoClientLogger().get_logger()