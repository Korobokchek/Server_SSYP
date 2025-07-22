import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QIcon
from video_client.client import VideoClient
from video_client.logger import logger


def main():
    """Точка входа в приложение"""
    try:
        logger.info("Starting application")
        app = QApplication(sys.argv)

        # Установка стиля Fusion (лучше выглядит в темном режиме)
        app.setStyle('Fusion')

        window = QMainWindow()
        window.setWindowTitle("Youtube")
        window.setGeometry(100, 100, 1200, 850)

        video_client = VideoClient()
        window.setCentralWidget(video_client.ui.main_widget)

        window.show()
        logger.info("Application started successfully")
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Application failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()