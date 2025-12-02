import sys
import os
import logging
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSettings

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Добавляем путь к src в sys.path для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ИМПОРТ ПОЛЬЗОВАТЕЛЬСКИХ МОДУЛЕЙ
try:
    from database import DataBase
    from login_window import LoginWindow
    from main_window import MainWindow
except ImportError as e:
    logger.critical(f"Ошибка импорта модулей: {e}")
    sys.exit(1)


class PuzzleVkusovApp:
    """Главный класс приложения 'Пазл Вкусов'"""
    def __init__(self):
        try:
            self.app = QApplication(sys.argv)
            self.settings = QSettings("PuzzleVkusov", "AppSettings")

            # НАСТРОЙКА ИКОНКИ ПРИЛОЖЕНИЯ
            icon_path = os.path.join(os.path.dirname(current_dir), 'img', 'ico2.ico')
            if os.path.exists(icon_path):
                self.app.setWindowIcon(QIcon(icon_path))

            # ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
            self.db = DataBase()
            self.current_user_id = None

            # ПРОВЕРКА АВТОМАТИЧЕСКОГО ВХОДА
            self.check_auto_login()

        except Exception as e:
            logger.critical(f"Ошибка инициализации приложения: {e}")
            self.show_error_message(f"Критическая ошибка инициализации: {e}")
            sys.exit(1)

    def show_error_message(self, message):
        """Показывает сообщение об ошибке"""
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setWindowTitle("Ошибка")
        error_box.setText(message)
        error_box.exec()

    def check_auto_login(self):
        """Проверяет, нужно ли автоматически войти в систему"""
        try:
            auto_login = self.settings.value("auto_login", False, type=bool)
            if auto_login:
                user_id = self.settings.value("user_id", None, type=int)
                if user_id:
                    self.current_user_id = user_id
                    self.show_main_window() # Показ главного окна
                    return
            self.show_login() # Показ окна входа
        except Exception as e:
            logger.error(f"Ошибка автоматического входа: {e}")
            self.show_login()

    def show_login(self):
        """Метод для отображения окна входа"""
        try:
            self.login_window = LoginWindow(self.db, self.on_login_success)
            self.login_window.show()
        except Exception as e:
            logger.error(f"Ошибка создания окна входа: {e}")
            self.show_error_message(f"Ошибка создания окна входа: {e}")

    def on_login_success(self, user_id):
        """Callback-функция, вызываемая после успешного входа"""
        try:
            self.current_user_id = user_id
            if hasattr(self, 'login_window'):
                self.login_window.close() # Закрытие окна входа
            self.show_main_window() # Показ главного окна
        except Exception as e:
            logger.error(f"Ошибка после успешного входа: {e}")
            self.show_error_message(f"Ошибка после входа: {e}")

    def show_main_window(self):
        """Отображение главного окна приложения"""
        try:
            # ЗАГРУЗКА КОРЗИНЫ ИЗ БАЗЫ ДАННЫХ ПЕРЕД СОЗДАНИЕМ ГЛАВНОГО ОКНА
            cart_items = self.db.get_cart_items(self.current_user_id)
            logger.info(f"Загружено {len(cart_items)} элементов корзины для пользователя {self.current_user_id}")

            self.main_window = MainWindow(self.db, self.current_user_id, self.logout)
            self.main_window.show()
        except Exception as e:
            logger.error(f"Ошибка создания главного окна: {e}")
            self.show_error_message(f"Ошибка создания главного окна: {e}")

    def logout(self):
        """Выход из системы с очисткой настроек авто-входа"""
        try:
            # ОЧИСТКА НАСТРОЕК АВТОМАТИЧЕСКОГО ВХОДА
            self.settings.setValue("auto_login", False)
            self.settings.setValue("user_id", None)

            # ЗАКРЫТИЕ ГЛАВНОГО ОКНА И ПОКАЗ ОКНА ВХОДА
            if hasattr(self, 'main_window'):
                self.main_window.close()
            self.current_user_id = None
            self.show_login()
        except Exception as e:
            logger.error(f"Ошибка при выходе из системы: {e}")
            self.show_error_message(f"Ошибка при выходе: {e}")

    def run(self):
        """Запуск основного цикла приложения"""
        try:
            return self.app.exec()
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске приложения: {e}")
            return 1


if __name__ == "__main__":
    try:
        puzzle_app = PuzzleVkusovApp()
        sys.exit(puzzle_app.run())
    except Exception as e:
        logger.critical(f"Непредвиденная ошибка: {e}")
        sys.exit(1)