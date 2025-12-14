from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QCheckBox, QMessageBox, QFormLayout, QGroupBox,
                             QSpinBox, QTabWidget, QWidget)
from PyQt6.QtCore import QSettings, pyqtSignal


class SettingsDialog(QDialog):
    """Диалоговое окно настроек приложения с сохранением параметров"""

    # Сигнал для уведомления главного окна об изменении настроек
    settings_updated = pyqtSignal(dict)

    def __init__(self, db, user_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id
        self.settings = QSettings("PuzzleVkusov", "AppSettings")
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Инициализация пользовательского интерфейса диалога настроек"""
        self.setWindowTitle("Настройки приложения")
        self.setFixedSize(800, 600)

        # НАСТРОЙКА ИКОНКИ ОКНА
        self.setWindowIcon(QIcon("../img/icon.ico"))

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # СОЗДАНИЕ ВКЛАДОК ДЛЯ РАЗНЫХ КАТЕГОРИЙ НАСТРОЕК
        self.tabs = QTabWidget()

        # ВКЛАДКА "ОСНОВНЫЕ НАСТРОЙКИ"
        general_tab = QWidget()
        general_layout = QVBoxLayout()

        general_group = QGroupBox("Общие настройки")
        general_form = QFormLayout()

        self.auto_login = QCheckBox("Запомнить меня")
        general_form.addRow(self.auto_login)

        general_group.setLayout(general_form)
        general_layout.addWidget(general_group)

        # ГРУППА НАСТРОЕК ШРИФТА
        font_group = QGroupBox("Настройки шрифта")
        font_layout = QFormLayout()

        # Настройка основного размера шрифта
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 20)
        self.font_size.setValue(12)
        font_layout.addRow("Размер основного шрифта:", self.font_size)

        # Размер шрифта заголовков
        self.title_font_size = QSpinBox()
        self.title_font_size.setRange(10, 24)
        self.title_font_size.setValue(14)
        font_layout.addRow("Размер шрифта заголовков:", self.title_font_size)

        font_group.setLayout(font_layout)
        general_layout.addWidget(font_group)

        general_layout.addStretch()
        general_tab.setLayout(general_layout)

        # ДОБАВЛЕНИЕ ВКЛАДОК
        self.tabs.addTab(general_tab, "⚙️ Основные")

        layout.addWidget(self.tabs)

        # ПАНЕЛЬ КНОПОК УПРАВЛЕНИЯ
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton("💾 Сохранить")
        save_btn.clicked.connect(self.save_settings)

        cancel_btn = QPushButton("❌ Отмена")
        cancel_btn.clicked.connect(self.reject)

        reset_btn = QPushButton("🔄 Сбросить настройки")
        reset_btn.clicked.connect(self.reset_settings)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(reset_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def load_settings(self):
        """Загрузка текущих настроек"""
        try:
            # ЗАГРУЗКА ОБЩИХ НАСТРОЕК
            self.auto_login.setChecked(self.settings.value("auto_login", False, type=bool))

            # ЗАГРУЗКА НАСТРОЕК ШРИФТА
            self.font_size.setValue(self.settings.value("font_size", 14, type=int))
            self.title_font_size.setValue(self.settings.value("title_font_size", 16, type=int))

        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def save_settings(self):
        """Сохранение текущих настроек в хранилище"""
        try:
            # СОХРАНЕНИЕ ОБЩИХ НАСТРОЕК
            self.settings.setValue("auto_login", self.auto_login.isChecked())

            # СОХРАНЕНИЕ НАСТРОЕК ШРИФТА
            self.settings.setValue("font_size", self.font_size.value())
            self.settings.setValue("title_font_size", self.title_font_size.value())
            # СОХРАНЕНИЕ НАСТРОЕК УВЕДОМЛЕНИЙ

            # СОХРАНЕНИЕ ID ПОЛЬЗОВАТЕЛЯ ДЛЯ АВТОМАТИЧЕСКОГО ВХОДА
            if self.auto_login.isChecked():
                self.settings.setValue("user_id", self.user_id)
            else:
                self.settings.setValue("user_id", None)

            self.settings.sync() # Синхронизация настроек

            # ФОРМИРОВАНИЕ И ОТПРАВКА ДАННЫХ НАСТРОЕК
            settings_data = {
                'font_size': self.font_size.value(),
                'title_font_size': self.title_font_size.value(),
            }

            self.settings_updated.emit(settings_data) # Отправка сигнала
            QMessageBox.information(self, "Успех", "Настройки успешно сохранены!")
            self.accept()  # Закрытие окна с положительным результатом

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {e}")

    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы действительно хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.settings.clear()
                self.load_settings()
                QMessageBox.information(self, "Успех", "Настройки сброшены к значениям по умолчанию!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сбросить настройки: {e}")
