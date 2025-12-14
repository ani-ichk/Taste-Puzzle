from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                             QLineEdit, QLabel, QMessageBox, QTabWidget, QCheckBox)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon


class LoginWindow(QWidget):
    """Окно авторизации и регистрации пользователя"""

    def __init__(self, db, on_login_success):
        super().__init__()
        self.db = db
        self.on_login_success = on_login_success
        self.settings = QSettings("PuzzleVkusov", "AppSettings")
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle('Пазл Вкусов - Вход')
        self.setGeometry(300, 300, 400, 400)

        # НАСТРОЙКА ИКОНКИ ОКНА
        self.setWindowIcon(QIcon("../img/ico2.ico"))

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # СОЗДАНИЕ ВКЛАДОК ДЛЯ ВХОДА И РЕГИСТРАЦИИ
        self.tabs = QTabWidget()

        # ВКЛАДКА "ВХОД В СИСТЕМУ"
        login_tab = QWidget()
        login_layout = QVBoxLayout()
        login_layout.setSpacing(15)

        login_title = QLabel("Вход в систему")
        login_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        login_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        login_layout.addWidget(login_title)

        self.login_username = QLineEdit()
        self.login_username.setPlaceholderText("Введите логин")
        self.login_username.setStyleSheet("padding: 10px; font-size: 14px;")

        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Введите пароль")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setStyleSheet("padding: 10px; font-size: 14px;")

        self.remember_me = QCheckBox("Запомнить меня")
        self.remember_me.setStyleSheet("""
            QCheckBox {
                color: #495057;
                font-size: 12px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        login_btn = QPushButton("Войти")
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        login_btn.clicked.connect(self.handle_login)

        login_layout.addWidget(self.login_username)
        login_layout.addWidget(self.login_password)
        login_layout.addWidget(self.remember_me)
        login_layout.addWidget(login_btn)
        login_tab.setLayout(login_layout)

        # ВКЛАДКА "РЕГИСТРАЦИЯ"
        register_tab = QWidget()
        register_layout = QVBoxLayout()
        register_layout.setSpacing(15)

        register_title = QLabel("Регистрация")
        register_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        register_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_layout.addWidget(register_title)

        self.register_username = QLineEdit()
        self.register_username.setPlaceholderText("Придумайте логин")
        self.register_username.setStyleSheet("padding: 10px; font-size: 14px;")

        self.register_password = QLineEdit()
        self.register_password.setPlaceholderText("Придумайте пароль, не менее 6 символов")
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password.setStyleSheet("padding: 10px; font-size: 14px;")

        self.register_confirm_password = QLineEdit()
        self.register_confirm_password.setPlaceholderText("Повторите пароль")
        self.register_confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_confirm_password.setStyleSheet("padding: 10px; font-size: 14px;")

        register_btn = QPushButton("Зарегистрироваться")
        register_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #28a745;
                        color: white;
                        padding: 12px;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                """)
        register_btn.clicked.connect(self.handle_register)

        register_layout.addWidget(self.register_username)
        register_layout.addWidget(self.register_password)
        register_layout.addWidget(self.register_confirm_password)
        register_layout.addWidget(register_btn)
        register_tab.setLayout(register_layout)

        # ДОБАВЛЕНИЕ ВКЛАДОК
        self.tabs.addTab(login_tab, "Вход")
        self.tabs.addTab(register_tab, "Регистрация")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def handle_login(self):
        """Обработчик нажатия кнопки входа"""
        username = self.login_username.text().strip()
        password = self.login_password.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        # АУТЕНТИФИКАЦИЯ ПОЛЬЗОВАТЕЛЯ
        users = self.db.get_users(username, password)
        if users:
            user_id = users[0][0]

            # СОХРАНЕНИЕ НАСТРОЕК АВТОМАТИЧЕСКОГО ВХОДА
            if self.remember_me.isChecked():
                self.settings.setValue("auto_login", True)
                self.settings.setValue("user_id", user_id)
            else:
                self.settings.setValue("auto_login", False)
                self.settings.setValue("user_id", None)

            self.on_login_success(user_id)
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def handle_register(self):
        """Обработчик нажатия кнопки регистрации"""
        username = self.register_username.text().strip()
        password = self.register_password.text()
        confirm_password = self.register_confirm_password.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен содержать не меньше 6 символов")
            return

        # РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ В БАЗЕ ДАННЫХ
        success, message = self.db.register_user(username, password)
        if success:
            QMessageBox.information(self, "Успех", "Регистрация прошла успешно!")

            self.tabs.setCurrentIndex(0)
            self.login_username.setText(username)
            self.login_password.clear()

            # Очищаем поля регистрации
            self.register_username.clear()
            self.register_password.clear()
            self.register_confirm_password.clear()
        else:
            QMessageBox.warning(self, "Ошибка", message)

    def load_saved_credentials(self):
        """Загружает сохраненные учетные данные"""
        try:
            remember_me = self.settings.value("remember_me", False, type=bool)
            if remember_me:
                username = self.settings.value("username", "")
                if username:
                    self.login_username.setText(username)
                    self.remember_me.setChecked(True)
                    print(f"Загружен сохраненный логин: {username}")
        except Exception as e:
            print(f"Ошибка при загрузке сохраненных данных: {e}")

    def save_credentials(self):
        """Сохраняет или очищает учетные данные"""
        if self.remember_me.isChecked():
            username = self.login_username.text().strip()
            if username:
                self.settings.setValue("remember_me", True)
                self.settings.setValue("username", username)
                print(f"Сохранен логин: {username}")
        else:
            self.settings.setValue("remember_me", False)
            self.settings.setValue("username", "")
            print("Данные для запоминания очищены")
