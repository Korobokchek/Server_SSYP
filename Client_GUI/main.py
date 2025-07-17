import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from video_client.client import VideoClient
from video_client.logger import logger


def main():
    """Точка входа в приложение"""
    try:
        logger.info("Starting application")
        app = QApplication(sys.argv)

        window = QMainWindow()
        window.setWindowTitle("Видеоплеер-клиент")
        window.setGeometry(100, 100, 1000, 700)

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