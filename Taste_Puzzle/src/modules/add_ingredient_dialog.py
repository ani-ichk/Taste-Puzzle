import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                            QLabel, QLineEdit, QComboBox, QDoubleSpinBox,
                            QMessageBox)
from PyQt6.QtCore import Qt

# Добавляем путь для импорта database
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.database import DataBase


class AddIngredientDialog(QDialog):
    """Диалог для добавления пользовательских ингредиентов в корзину"""

    def __init__(self, db, parent=None):
        """ Инициализация диалога добавления ингредиента """
        super().__init__(parent)
        self.db = db
        self.ingredient_data = None # Данные добавленного ингредиента
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Добавить ингредиент")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # ПОЛЕ ВВОДА НАЗВАНИЯ ИНГРЕДИЕНТА
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Ингредиент:"))

        # Выпадающий список существующих ингредиентов
        self.name_combo = QComboBox()
        # Заполняем список существующими ингредиентами
        ingredients = self.db.get_ingredients() # Получение ингредиентов из БД
        for ing_id, ing_name in ingredients:
            self.name_combo.addItem(ing_name)

        # Поле для ввода нового ингредиента
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Или введите новый ингредиент...")

        name_layout.addWidget(self.name_combo)
        name_layout.addWidget(self.custom_name_input)
        layout.addLayout(name_layout)

        # ПОЛЯ ДЛЯ ВВОДА КОЛИЧЕСТВА И ЕДИНИЦЫ ИЗМЕРЕНИЯ
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(QLabel("Количество:"))

        # Спинбокс для ввода количества
        self.quantity_input = QDoubleSpinBox()
        self.quantity_input.setRange(0.1, 10000)  # Диапазон значений
        self.quantity_input.setDecimals(2) # Два знака после запятой
        self.quantity_input.setValue(100) # Значение по умолчанию

        # Выпадающий список единиц измерения
        self.unit_combo = QComboBox()
        units = ["г", "кг", "мл", "л", "шт", "ст.л.", "ч.л.", "стакан", "щепотка", "по вкусу"]
        self.unit_combo.addItems(units)

        quantity_layout.addWidget(self.quantity_input)
        quantity_layout.addWidget(self.unit_combo)
        quantity_layout.addStretch() # Растягиваемое пространство
        layout.addLayout(quantity_layout)

        # ПАНЕЛЬ КНОПОК УПРАВЛЕНИЯ
        buttons_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_ingredient)  # Добавление ингредиента

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject) # Закрытие без добавления

        buttons_layout.addWidget(add_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def add_ingredient(self):
        """Добавление ингредиента в корзину с валидацией данных"""
        # ПОЛУЧЕНИЕ НАЗВАНИЯ ИНГРЕДИЕНТА
        name = self.custom_name_input.text().strip()
        if not name:
            name = self.name_combo.currentText() # Использование выбранного из списка

        # ПРОВЕРКА НАЛИЧИЯ НАЗВАНИЯ
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название ингредиента")
            return

        # ПОЛУЧЕНИЕ КОЛИЧЕСТВА И ЕДИНИЦЫ ИЗМЕРЕНИЯ
        quantity = self.quantity_input.value()
        unit = self.unit_combo.currentText()

        # СОХРАНЕНИЕ ДАННЫХ ИНГРЕДИЕНТА
        self.ingredient_data = {
            'name': name,
            'quantity': quantity,
            'unit': unit
        }

        # Если это новый ингредиент, добавляем его в базу
        if name == self.custom_name_input.text().strip():
            self.db.add_ingredient(name)

        self.accept()

    def get_ingredient_data(self):
        """Возвращает данные ингредиента"""
        return self.ingredient_data